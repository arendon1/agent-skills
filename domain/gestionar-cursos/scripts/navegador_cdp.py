"""
Navegador via Chrome DevTools Protocol (CDP).

Estrategia (anclada al PERFIL, no al puerto):
1. Descubrir qué perfil Chrome sirve cada endpoint CDP vivo del rango de
   puertos — preguntándole al propio endpoint (Browser.getBrowserCommandLine,
   con fallback al listener del SO).
2. Si el perfil autorizado ya está vivo, conectarse a SU puerto.
3. Si no, lanzar Chrome con ese perfil en el primer puerto libre.
4. Verificar el amarre perfil<->puerto ANTES de attachar: nunca operar un
   perfil fuera de la allowlist de ~/.agents/.

Ventaja: el usuario puede tener sesión activa en Chrome.
El script se conecta a esa instancia y navega automáticamente.
"""

import atexit
import contextlib
import os
import re
import socket
import subprocess
import time

from rich.console import Console
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

console = Console()

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"/usr/bin/google-chrome",
    r"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

# --- Identidad: el PERFIL, no el puerto ----------------------------------
# El puerto es efímero (puede variar según disponibilidad); el perfil no.
# Por eso la heurística se ancla SIEMPRE al perfil al que está amarrado cada
# puerto: se descubren los endpoints CDP, se le pregunta a cada uno qué perfil
# usa, y se resuelve perfil -> puerto. Nunca se asume que un número de puerto
# corresponde a un perfil.
#
# Política de Andrés (2026-09-11): solo dos perfiles Chrome autorizados para
# agentes, y ambos viven exclusivamente dentro de ~/.agents/.
PROFILE_MOODLE = "~/.agents/.browserdata"
PROFILE_GLOBANT = "~/.agents/.browserdata-globant"
AUTHORIZED_PROFILES = (PROFILE_MOODLE, PROFILE_GLOBANT)
CANONICAL_PROFILE_DIR = os.path.expanduser(PROFILE_MOODLE)

# Rango donde se descubren/abren endpoints CDP. NO es un mapa puerto->perfil.
CDP_PORT_RANGE = range(9222, 9240)

# Perfiles EFÍMEROS de prueba: viven en /tmp, son de un solo uso, NO se
# persisten ni se adoptan como perfil de agente.
# OJO: el navegador interno de cmux es una **WKWebView**, no un proceso Chrome:
# no abre puerto CDP y por eso NUNCA aparece en este inventario. Los
# /tmp/cmux-chrome-<proyecto>-<epoch> son Chrome de prueba lanzados a través
# de cmux, no su navegador interno.
PREFIJOS_EFIMEROS = ("cmux-chrome-",)

_driver = None
_cdp_launched_by_us = False
_profile_dir = None  # Se configura antes de _launch_chrome_cdp()
_puerto_activo = None  # Puerto resuelto para el perfil actual


def _normalize_profile(path: str) -> str:
    """Ruta absoluta y sin symlinks — la forma estable de comparar perfiles."""
    return os.path.realpath(os.path.expanduser(str(path)))


def _authorized_dirs() -> set:
    return {_normalize_profile(p) for p in AUTHORIZED_PROFILES}


def is_authorized(path: str) -> bool:
    """True si `path` es uno de los perfiles autorizados."""
    return _normalize_profile(path) in _authorized_dirs()


def clasificar_perfil(path: str) -> str:
    """Clase de un perfil descubierto: 'autorizado' | 'efimero' | 'desconocido'.

    El navegador interno de cmux no entra en esta clasificación: es una
    WKWebView, no publica CDP. Un 'efimero' es un Chrome de prueba en /tmp —
    se ignora y no se persiste.
    """
    if is_authorized(path):
        return "autorizado"
    base = os.path.basename(_normalize_profile(path))
    if base.startswith(PREFIJOS_EFIMEROS):
        return "efimero"
    return "desconocido"


def _sugerencia_perfil(path: str) -> str | None:
    """Si `path` parece un perfil autorizado mal ubicado, sugiere la buena."""
    base = os.path.basename(_normalize_profile(path))
    for autorizado in AUTHORIZED_PROFILES:
        if os.path.basename(_normalize_profile(autorizado)) == base:
            return autorizado
    return None


def _assert_authorized(path: str) -> str:
    """Valida contra la allowlist y devuelve la ruta normalizada.

    El error es accionable a propósito: no solo bloquea, dice dónde vive el
    perfil que probablemente se quería usar."""
    norm = _normalize_profile(path)
    if norm not in _authorized_dirs():
        sugerencia = _sugerencia_perfil(path)
        extra = (
            f"\n¿Querías decir {sugerencia}? Todo perfil de agente vive en ~/.agents/."
            if sugerencia
            else ""
        )
        raise ValueError(
            f"Perfil Chrome NO autorizado: {path}\n"
            "Solo se permite operar por CDP con estos perfiles: "
            + ", ".join(AUTHORIZED_PROFILES)
            + extra
        )
    return norm


def set_profile_dir(path: str):
    """Establece el perfil de Chrome (validado contra la allowlist).
    La ruta debe ser uno de los perfiles autorizados dentro de ~/.agents/."""
    global _profile_dir
    _profile_dir = _assert_authorized(path)
    os.makedirs(_profile_dir, exist_ok=True)


def get_profile_dir() -> str:
    """Retorna el directorio de perfil actual (canónico si no se configuró)."""
    global _profile_dir
    if _profile_dir:
        return _profile_dir
    # Default canónico: perfil único de navegador para agentes
    os.makedirs(CANONICAL_PROFILE_DIR, exist_ok=True)
    return CANONICAL_PROFILE_DIR


def _find_chrome() -> str | None:
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    return None


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (TimeoutError, ConnectionRefusedError, OSError):
        return False


# --- Descubrimiento: ¿qué perfil está amarrado a este puerto? -------------

def _cdp_version(port: int, timeout: float = 1.0) -> dict:
    """GET /json/version del endpoint CDP en `port`."""
    import json as _json
    import urllib.request

    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}/json/version", timeout=timeout
    ) as resp:
        return _json.loads(resp.read().decode("utf-8", "replace"))


def _user_data_dir_de(args) -> str | None:
    """Extrae --user-data-dir de una lista de argumentos de Chrome."""
    for arg in args or []:
        if isinstance(arg, str) and arg.startswith("--user-data-dir="):
            return arg.split("=", 1)[1]
    return None


def _user_data_dir_via_cdp(ws_url: str) -> str | None:
    """El endpoint se autodescribe: Browser.getBrowserCommandLine."""
    import json as _json

    import websocket

    conn = websocket.create_connection(ws_url, timeout=3, suppress_origin=True)
    try:
        conn.send(_json.dumps({"id": 1, "method": "Browser.getBrowserCommandLine"}))
        for _ in range(10):
            msg = _json.loads(conn.recv())
            if msg.get("id") == 1:
                return _user_data_dir_de((msg.get("result") or {}).get("arguments"))
    finally:
        conn.close()
    return None


def _user_data_dir_del_listener(port: int) -> str | None:
    """Fallback sin CDP: preguntar al SO qué proceso escucha en el puerto."""
    try:
        out = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fp"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None

    for line in out.splitlines():
        if not line.startswith("p"):
            continue
        pid = line[1:].strip()
        try:
            cmd = subprocess.run(
                ["ps", "-o", "command=", "-p", pid],
                capture_output=True, text=True, timeout=5,
            ).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        encontrado = _user_data_dir_de(re.findall(r"--user-data-dir=\S+", cmd))
        if encontrado:
            return encontrado
    return None


def perfil_de_puerto(port: int) -> str | None:
    """Perfil Chrome amarrado a `port`, o None si no hay endpoint CDP ahí."""
    try:
        version = _cdp_version(port)
    except Exception:
        return None

    ws_url = version.get("webSocketDebuggerUrl")
    if ws_url:
        try:
            perfil = _user_data_dir_via_cdp(ws_url)
            if perfil:
                return perfil
        except Exception:
            pass

    return _user_data_dir_del_listener(port)


def inventario_cdp(puertos=None) -> list:
    """Topología CDP viva: [{'puerto', 'perfil', 'clase'}]. Solo lectura."""
    filas = []
    for port in (CDP_PORT_RANGE if puertos is None else puertos):
        perfil = perfil_de_puerto(port)
        if perfil:
            filas.append({
                "puerto": port,
                "perfil": _normalize_profile(perfil),
                "clase": clasificar_perfil(perfil),
            })
    return filas


def descubrir_perfiles(puertos=None) -> dict:
    """{perfil_normalizado: puerto} para cada endpoint CDP vivo del rango."""
    return {fila["perfil"]: fila["puerto"] for fila in inventario_cdp(puertos)}


def _reportar_endpoints_ajenos(filas) -> None:
    """Nombra lo que NO nos pertenece: efímero de prueba vs. desconocido."""
    for fila in filas:
        clase = fila["clase"]
        if clase == "autorizado":
            continue
        if clase == "efimero":
            console.print(
                f"[dim]· CDP :{fila['puerto']} → perfil efímero de prueba "
                f"({fila['perfil']}) — ignorado, no se persiste.[/dim]"
            )
        else:
            console.print(
                f"[yellow]⚠[/yellow] CDP :{fila['puerto']} usa un perfil fuera de la "
                f"allowlist ({fila['perfil']}) — ignorado."
            )


def puerto_para_perfil(profile: str) -> int | None:
    """Puerto donde vive ESTE perfil, sea cual sea el número que tenga.

    Nombra lo ajeno sin tocarlo (p. ej. un Chrome de prueba efímero en /tmp)
    y sigue con el perfil autorizado. El navegador interno de cmux es una
    WKWebView: no publica CDP, así que no interfiere."""
    objetivo = _assert_authorized(profile)
    filas = inventario_cdp()
    _reportar_endpoints_ajenos(filas)

    for fila in filas:
        if fila["perfil"] == objetivo:
            return fila["puerto"]
    return None


def _puerto_libre() -> int:
    """Primer puerto del rango sin listener."""
    for port in CDP_PORT_RANGE:
        if not _is_port_open("localhost", port):
            return port
    raise RuntimeError(
        f"No hay puertos libres para CDP en el rango "
        f"{CDP_PORT_RANGE.start}-{CDP_PORT_RANGE.stop - 1}."
    )


def _launch_chrome_cdp(puerto: int | None = None) -> int:
    """Lanza Chrome con CDP usando el perfil autorizado.
    Devuelve el puerto efectivamente usado (varía según disponibilidad)."""
    global _cdp_launched_by_us, _puerto_activo

    chrome_path = _find_chrome()
    if not chrome_path:
        raise RuntimeError(
            "No se encontró Google Chrome. "
            "Instálalo o define la ruta en CHROME_PATHS."
        )

    user_data_dir = _assert_authorized(get_profile_dir())
    os.makedirs(user_data_dir, exist_ok=True)

    # Limpiar lock files de sesiones previas crash/crash
    _cleanup_chrome_locks(user_data_dir)

    port = _puerto_libre() if puerto is None else puerto

    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
    ]

    console.print(f"[dim][CDP] Lanzando Chrome:[/dim] {chrome_path}")
    console.print(f"[dim][CDP] Perfil autorizado:[/dim] {user_data_dir}")
    console.print(f"[dim][CDP] Puerto:[/dim] {port}")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _cdp_launched_by_us = True
    _puerto_activo = port
    time.sleep(3)  # Esperar arranque
    return port


def _cleanup_chrome_locks(profile_dir: str):
    """Elimina archivos de lock de Chrome que impiden re-apertura."""
    lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie",
                  "lockfile", "Local State.bak"]
    for name in lock_files:
        path = os.path.join(profile_dir, name)
        if os.path.exists(path):
            with contextlib.suppress(OSError):
                os.remove(path)


def _conectar_driver():
    """Conecta Selenium al Chrome que sirve al PERFIL configurado.

    El puerto se resuelve por descubrimiento (perfil -> puerto), nunca al
    revés: si el perfil ya está vivo en cualquier puerto del rango, se usa
    ése; si no, se abre uno propio en un puerto libre."""
    global _driver, _puerto_activo
    if _driver is not None:
        return _driver

    perfil = _assert_authorized(get_profile_dir())

    # 1) Puerto memorizado, si todavía sirve a ESTE perfil.
    puerto = _puerto_activo
    if puerto is not None:
        vivo = perfil_de_puerto(puerto)
        if vivo is None or _normalize_profile(vivo) != perfil:
            puerto = None

    # 2) Descubrimiento: ¿algún endpoint CDP vivo sirve ya a este perfil?
    if puerto is None:
        puerto = puerto_para_perfil(perfil)

    # 3) Si no, abrir Chrome propio con ESE perfil, en un puerto libre.
    if puerto is None:
        puerto = _launch_chrome_cdp()
        for _ in range(10):
            if _is_port_open("localhost", puerto):
                break
            time.sleep(1)
        else:
            raise RuntimeError("Chrome no abrió el puerto de debugging.")

    # 4) Verificación final: el puerto elegido debe servir EXACTAMENTE al
    #    perfil autorizado. Nunca attacharse a un perfil ajeno.
    real = perfil_de_puerto(puerto)
    if real is None or _normalize_profile(real) != perfil:
        raise RuntimeError(
            f"El endpoint CDP :{puerto} no sirve al perfil autorizado "
            f"({perfil}); sirve a {real!r}. Abortando para no operar un "
            "perfil no autorizado."
        )

    _puerto_activo = puerto
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{puerto}")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    try:
        _driver = webdriver.Chrome(options=opts)
    except WebDriverException as e:
        raise RuntimeError(f"No se pudo conectar a Chrome CDP: {e}") from e

    atexit.register(_cerrar)
    return _driver


def _cerrar():
    global _driver, _cdp_launched_by_us
    if _driver:
        _driver.quit()
        _driver = None
    if _cdp_launched_by_us:
        # No matamos el proceso Chrome para no cerrar sesiones del usuario
        pass


def get_driver():
    return _conectar_driver()


def navegar(url: str):
    driver = get_driver()
    driver.get(url)
    esperar_carga()


def obtener_url_actual() -> str:
    return get_driver().current_url


def obtener_contenido() -> str:
    return get_driver().page_source


def click(selector):
    driver = get_driver()
    if hasattr(selector, "click"):
        selector.click()
    else:
        # selector es un string: intentar CSS luego XPATH
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            el = driver.find_element(By.XPATH, selector)
        el.click()
    time.sleep(0.5)


def esperar_carga(timeout: int = 15):
    WebDriverWait(get_driver(), timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def esperar_selector(selector: str, timeout: int = 10):
    WebDriverWait(get_driver(), timeout).until(
        ec.presence_of_element_located((By.CSS_SELECTOR, selector))
    )


def encontrar_elementos(selector: str) -> list:
    return get_driver().find_elements(By.CSS_SELECTOR, selector)


def encontrar_menus_cerrados() -> list:
    """Encuentra secciones colapsadas de Moodle."""
    try:
        # Moodle usa aria-expanded="false" en toggles de sección
        return encontrar_elementos('[aria-expanded="false"]')
    except Exception:
        return []


def _detectar_tipo_modulo(href: str) -> str:
    """Detecta tipo de módulo Moodle desde URL."""
    if "/mod/page/" in href:
        return "page"
    elif "/mod/resource/" in href:
        return "resource"
    elif "/mod/forum/" in href:
        return "forum"
    elif "/mod/quiz/" in href:
        return "quiz"
    elif "/mod/folder/" in href:
        return "folder"
    elif "/mod/hvp/" in href:
        return "hvp"
    elif "/mod/url/" in href:
        return "url"
    elif "/mod/assign/" in href:
        return "assign"
    elif "/mod/choice/" in href:
        return "choice"
    elif "/mod/lesson/" in href:
        return "lesson"
    elif "/mod/workshop/" in href:
        return "workshop"
    elif "/l/meetup-join/" in href or "/l/channel/" in href:
        return "url"
    elif "/mod/label/" in href:
        return "label"
    return "unknown"


def _limpiar_nombre_actividad(link_el) -> str:
    """Extrae solo el nombre de la actividad, sin tipo pegado."""
    from bs4 import BeautifulSoup
    # Clonar para no mutar el soup original
    a_soup = BeautifulSoup(str(link_el), 'lxml')
    # Remover elementos de accesibilidad que pegan el tipo
    for cls in ['.accesshide', '.sr-only', '.visually-hidden']:
        for el in a_soup.select(cls):
            el.decompose()
    texto = a_soup.get_text(strip=True)
    # Fallback: quitar palabras de tipo conocidas al final
    for tipo_word in [
        'Página', 'Archivo', 'Carpeta', 'Cuestionario', 'Contenido interactivo',
        'Foro', 'Tarea', 'Etiqueta', 'Label', 'URL', 'H5P',
    ]:
        if texto.endswith(tipo_word):
            texto = texto[:-len(tipo_word)].strip()
    return texto


def _extraer_section_num(sec) -> str:
    """Extrae número de sección desde atributos id o data-sectionid."""
    sec_id = sec.get('id', '')
    m = None
    if sec_id:
        m = re.search(r'section-(\d+)', sec_id)
    if m:
        return m.group(1)
    data_sec = sec.get('data-sectionid', '')
    if data_sec:
        return str(data_sec)
    return ""


def extraer_sidebar() -> list[dict]:
    """Extrae items del curso desde page_source usando BeautifulSoup."""
    from bs4 import BeautifulSoup
    driver = get_driver()
    items = []
    try:
        soup = BeautifulSoup(driver.page_source, 'lxml')

        # ---- Formato Topics (lista tradicional) ----
        secciones = soup.select('li.section.main, li.course-section')
        for sec in secciones:
            nombre_el = sec.select_one('.sectionname, .course-section-name, h3')
            nombre = nombre_el.get_text(strip=True) if nombre_el else sec.get_text(strip=True).split('\n')[0]
            section_num = _extraer_section_num(sec)
            if nombre:
                items.append({"nombre": nombre, "url": "", "tipo": "seccion",
                              "section_num": section_num})

            for act in sec.select('li.activity'):
                link_el = act.select_one('a')
                if not link_el:
                    continue
                href = link_el.get('href', '')
                act_nombre = _limpiar_nombre_actividad(link_el)
                if act_nombre and href:
                    items.append({"nombre": act_nombre, "url": href,
                                  "tipo": _detectar_tipo_modulo(href)})

        # ---- Formato Grid (tarjetas) ----
        grid_sections = soup.select('.grid-section')
        for sec in grid_sections:
            # Título de la tarjeta
            nombre = sec.get('title', '') or sec.get_text(strip=True).split('\n')[0]
            section_num = _extraer_section_num(sec)
            if nombre:
                items.append({"nombre": nombre, "url": "", "tipo": "seccion",
                              "section_num": section_num})

            # Buscar popup/modal asociado
            sec_id = sec.get('id', '')  # ej: section-1
            if sec_id:
                popup = soup.select_one(f'#{sec_id.replace("section-", "gridpopupsection-")}')
                if popup:
                    for act in popup.select('li.activity'):
                        link_el = act.select_one('a')
                        if not link_el:
                            continue
                        href = link_el.get('href', '')
                        act_nombre = _limpiar_nombre_actividad(link_el)
                        if act_nombre and href:
                            items.append({"nombre": act_nombre, "url": href,
                                          "tipo": _detectar_tipo_modulo(href)})

            # También buscar actividades dentro del propio grid-section
            for act in sec.select('li.activity'):
                link_el = act.select_one('a')
                if not link_el:
                    continue
                href = link_el.get('href', '')
                act_nombre = _limpiar_nombre_actividad(link_el)
                if act_nombre and href:
                    items.append({"nombre": act_nombre, "url": href,
                                  "tipo": _detectar_tipo_modulo(href)})
    except Exception:
        pass
    return items


def abrir_popup_grid_y_obtener_html(nombre_seccion: str) -> str:
    """En formato Grid, hace click en la tarjeta de la sección y retorna el HTML del popup."""
    import time

    from bs4 import BeautifulSoup
    driver = get_driver()
    soup = BeautifulSoup(driver.page_source, 'lxml')

    for sec in soup.select('.grid-section'):
        titulo = sec.get('title', '') or sec.get_text(strip=True).split('\n')[0]
        if nombre_seccion.lower() in titulo.lower():
            sec_id = sec.get('id', '')
            if not sec_id:
                continue
            try:
                click(f'#{sec_id}')
                time.sleep(2)
                return obtener_contenido()
            except Exception:
                pass
            break
    return driver.page_source


def extraer_texto_descripcion() -> str:
    driver = get_driver()
    for selector in [
        '.activity-description',
        '#intro',
        '.content',
        '.description',
        '.summary',
    ]:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text
        except NoSuchElementException:
            continue
    return ""


def extraer_instrucciones() -> str:
    driver = get_driver()
    for selector in [
        '.submissioninstructions',
        '.generalbox',
        '.instrucciones',
        '.box.generalbox',
    ]:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text
        except NoSuchElementException:
            continue
    return ""


def extraer_links_materiales() -> list[str]:
    driver = get_driver()
    links = []
    try:
        for a in driver.find_elements(By.CSS_SELECTOR, 'a[href*="pluginfile.php"]'):
            href = a.get_attribute('href')
            if href:
                links.append(href)
    except Exception:
        pass
    return links


def extraer_criterios() -> str:
    driver = get_driver()
    for selector in [
        '.gradingform',
        '.criteria',
        '.criterios',
        '.grade-criteria',
    ]:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text
        except NoSuchElementException:
            continue
    return ""


def extraer_nombre_unidad() -> str:
    driver = get_driver()
    for selector in ['h1', '.sectionname', '.course-section-name', '.page-header-headings h1']:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            continue
    return "Unidad"


def obtener_cookies() -> str:
    driver = get_driver()
    cookies = driver.get_cookies()
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


def hacer_get(url: str, headers: dict | None = None) -> bytes:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    cookie_str = obtener_cookies()
    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers:
        req_headers.update(headers)
    req_headers["Cookie"] = cookie_str
    resp = requests.get(url, headers=req_headers, verify=False)
    resp.raise_for_status()
    return resp.content


def _normalizar_header(texto: str) -> str:
    """Normaliza texto de header para usar como clave de dict."""
    import unicodedata
    texto = texto.lower().strip()
    # Remover acentos
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    # Reemplazar espacios y caracteres especiales por _
    import re
    texto = re.sub(r'[^a-z0-9]+', '_', texto)
    texto = texto.strip('_')
    return texto


def _expandir_tabla(tabla) -> list[list[str]]:
    """Expande rowspan/colspan de una tabla HTML a matriz de texto."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(str(tabla), 'lxml')
    filas_tr = soup.find_all('tr')

    # Calcular número de columnas
    num_cols = 0
    for tr in filas_tr:
        celdas = tr.find_all(['td', 'th'])
        count = sum(int(c.get('colspan', 1)) for c in celdas)
        if count > num_cols:
            num_cols = count

    # Construir matriz expandiendo rowspan
    final_grid: list[list[str]] = []
    rowspan_map: dict[int, tuple[int, str]] = {}
    for tr in filas_tr:
        celdas = tr.find_all(['td', 'th'])
        fila = [''] * num_cols
        col_idx = 0
        for celda in celdas:
            texto = celda.get_text(strip=True)
            colspan = int(celda.get('colspan', 1))
            rowspan = int(celda.get('rowspan', 1))
            # Avanzar hasta encontrar celda vacía o ya llenada por rowspan previo
            while col_idx < num_cols and fila[col_idx] != '':
                col_idx += 1
            if col_idx >= num_cols:
                break
            fila[col_idx] = texto
            if rowspan > 1:
                rowspan_map[col_idx] = (rowspan - 1, texto)
            col_idx += colspan
        # Aplicar rowspan de filas anteriores
        for c in range(num_cols):
            if c in rowspan_map:
                remaining, texto = rowspan_map[c]
                if fila[c] == '':
                    fila[c] = texto
                rowspan_map[c] = (remaining - 1, texto)
                if remaining <= 1:
                    del rowspan_map[c]
        final_grid.append(fila)

    return final_grid


def _procesar_tabla_bs(tabla) -> list[dict]:
    """Convierte una tabla BeautifulSoup en lista de dicts."""
    grid = _expandir_tabla(tabla)
    if len(grid) < 2:
        return []

    # Buscar la fila con más celdas no vacías como headers
    max_celdas = 0
    idx_header = 0
    for i, fila in enumerate(grid):
        no_vacias = sum(1 for c in fila if c.strip())
        if no_vacias > max_celdas:
            max_celdas = no_vacias
            idx_header = i

    headers = [_normalizar_header(h) for h in grid[idx_header]]
    resultados = []
    for fila in grid[idx_header + 1:]:
        if not any(f.strip() for f in fila):
            continue
        resultados.append(dict(zip(headers, fila, strict=False)))

    return resultados


def _quitar_tildes(texto: str) -> str:
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


def extraer_filas_tabla(html_content: str, header_text: str) -> list[dict]:
    import re

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'lxml')
    header_norm = _quitar_tildes(header_text).lower()

    # Estrategia 1: header_text dentro de la tabla misma
    for tabla in soup.find_all('table'):
        texto_tabla = _quitar_tildes(tabla.get_text(separator=' ', strip=True)).lower()
        if header_norm in texto_tabla:
            resultado = _procesar_tabla_bs(tabla)
            if resultado:
                return resultado

    # Estrategia 2: header_text en ancestros cercanos (popups/modals Grid)
    for tabla in soup.find_all('table'):
        for ancestor in tabla.parents:
            if ancestor is None or ancestor.name == 'body':
                break
            texto_ancestor = _quitar_tildes(ancestor.get_text(separator=' ', strip=True)).lower()
            if header_norm in texto_ancestor:
                resultado = _procesar_tabla_bs(tabla)
                if resultado:
                    return resultado

    # Estrategia 3: buscar string con header_text y luego tabla cercana
    for elem in soup.find_all(
        string=re.compile(re.escape(header_text), re.IGNORECASE)
    ):
        for ancestor in [elem.parent] + list(elem.parents):
            if ancestor is None or ancestor.name == 'body':
                break
            tabla = ancestor.find('table')
            if tabla:
                resultado = _procesar_tabla_bs(tabla)
                if resultado:
                    return resultado

    return []


# --- Diagnóstico por línea de comandos ------------------------------------
# Uso: python scripts/navegador_cdp.py --inventario
#      python scripts/navegador_cdp.py --puerto-de '~/.agents/.browserdata'

if __name__ == "__main__":
    import argparse

    _etiqueta = {
        "autorizado": "✅ autorizado",
        "efimero": "· efímero de prueba",
        "desconocido": "⚠ fuera de allowlist",
    }

    _parser = argparse.ArgumentParser(
        description="Diagnóstico CDP anclado al PERFIL, no al puerto."
    )
    _parser.add_argument("--inventario", action="store_true",
                         help="Lista los endpoints CDP vivos con su perfil y clase")
    _parser.add_argument("--puerto-de", metavar="PERFIL",
                         help="Resuelve en qué puerto vive un perfil autorizado")
    _args = _parser.parse_args()

    if _args.puerto_de:
        _p = puerto_para_perfil(_args.puerto_de)
        print(_p if _p is not None else "(no está vivo)")
    else:
        _filas = inventario_cdp()
        if not _filas:
            print(f"(sin endpoints CDP vivos en "
                  f"{CDP_PORT_RANGE.start}-{CDP_PORT_RANGE.stop - 1})")
        for _f in _filas:
            print(f":{_f['puerto']:<6} {_etiqueta[_f['clase']]:<22} {_f['perfil']}")
