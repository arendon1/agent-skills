"""
Navegador via Chrome DevTools Protocol (CDP).

Estrategia:
1. Intentar conectar a Chrome existente en localhost:9222
2. Si no disponible, lanzar Chrome nuevo con --remote-debugging-port=9222
3. Usar Selenium con debuggerAddress para controlar la instancia

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

CDP_PORT = 9222
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"/usr/bin/google-chrome",
    r"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

_driver = None
_cdp_launched_by_us = False
_profile_dir = None  # Se configura antes de _launch_chrome_cdp()


def set_profile_dir(path: str):
    """Establece directorio persistente para perfil de Chrome (cookies, sesiones)."""
    global _profile_dir
    _profile_dir = os.path.abspath(path)


def get_profile_dir() -> str:
    """Retorna el directorio de perfil actual."""
    global _profile_dir
    if _profile_dir:
        return _profile_dir
    # Default: .browserdata en el directorio de trabajo actual
    return os.path.join(os.getcwd(), ".browserdata")


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


def _launch_chrome_cdp() -> str:
    """Lanza Chrome con puerto de debugging remoto.
    Usa perfil persistente en el workspace para mantener sesiones."""
    global _cdp_launched_by_us
    chrome_path = _find_chrome()
    if not chrome_path:
        raise RuntimeError(
            "No se encontró Google Chrome. "
            "Instálalo o define la ruta en CHROME_PATHS."
        )

    user_data_dir = get_profile_dir()
    os.makedirs(user_data_dir, exist_ok=True)

    # Limpiar lock files de sesiones previas crash/crash
    _cleanup_chrome_locks(user_data_dir)

    cmd = [
        chrome_path,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
    ]

    console.print(f"[dim][CDP] Lanzando Chrome:[/dim] {chrome_path}")
    console.print(f"[dim][CDP] Perfil persistente:[/dim] {user_data_dir}")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _cdp_launched_by_us = True
    time.sleep(3)  # Esperar arranque
    return chrome_path


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
    """Conecta Selenium a Chrome via CDP."""
    global _driver
    if _driver is not None:
        return _driver

    if not _is_port_open("localhost", CDP_PORT):
        _launch_chrome_cdp()
        # Esperar a que el puerto esté disponible
        for _ in range(10):
            if _is_port_open("localhost", CDP_PORT):
                break
            time.sleep(1)
        else:
            raise RuntimeError("Chrome no abrió el puerto de debugging.")

    opts = Options()
    opts.add_experimental_option("debuggerAddress", "localhost:9222")
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
