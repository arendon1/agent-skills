"""
Navegador via requests.Session + BeautifulSoup.
Backend alternativo a navegador_cdp.py para extracción sin navegador real.

La sesión (cookies, headers) se inyecta con set_session() antes de usar.
Todas las funciones de extracción usan BS4 sobre response.text.
"""

import re
import time
import unicodedata

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_session: requests.Session | None = None
_ultimo_url: str = ""
_ultimo_contenido: str = ""


def set_session(session: requests.Session):
    """Inyecta la sesión requests con cookies de Moodle."""
    global _session
    _session = session


def _check_session():
    if _session is None:
        raise RuntimeError(
            "Sesión requests no configurada. Llama set_session() primero."
        )


# ---------------------------------------------------------------------------
# Navegación básica
# ---------------------------------------------------------------------------

def navegar(url: str):
    """Navega a URL usando requests.Session. Guarda contenido internamente."""
    global _ultimo_url, _ultimo_contenido
    _check_session()
    resp = _session.get(url, timeout=60)
    resp.raise_for_status()
    _ultimo_url = resp.url
    _ultimo_contenido = resp.text


def obtener_url_actual() -> str:
    return _ultimo_url


def obtener_contenido() -> str:
    return _ultimo_contenido


def obtener_cookies() -> str:
    _check_session()
    return "; ".join(f"{c.name}={c.value}" for c in _session.cookies)


def hacer_get(url: str, headers: dict | None = None) -> bytes:
    _check_session()
    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers:
        req_headers.update(headers)
    resp = _session.get(url, headers=req_headers, verify=False, timeout=60)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# Funciones interactivas (no-ops o BS4 equivalentes)
# ---------------------------------------------------------------------------

def click(selector):
    """No-op en modo requests. El contenido ya está en el HTML."""
    pass


def esperar_carga(timeout: int = 15):
    """No-op en modo requests. No hay carga asíncrona."""
    pass


def esperar_selector(selector: str, timeout: int = 10):
    """Verifica que el selector exista en el contenido actual."""
    soup = BeautifulSoup(_ultimo_contenido, "lxml")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if soup.select_one(selector):
            return
        time.sleep(0.3)
    # No raise — el contenido puede no tener el selector en requests mode


def encontrar_elementos(selector: str) -> list:
    soup = BeautifulSoup(_ultimo_contenido, "lxml")
    return soup.select(selector)


def encontrar_menus_cerrados() -> list:
    """Encuentra secciones colapsadas de Moodle (aria-expanded=false)."""
    try:
        soup = BeautifulSoup(_ultimo_contenido, "lxml")
        return soup.select('[aria-expanded="false"]')
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Utilidades de parsing (idénticas a navegador_cdp.py)
# ---------------------------------------------------------------------------

def _detectar_tipo_modulo(href: str) -> str:
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
    a_soup = BeautifulSoup(str(link_el), "lxml")
    for cls in [".accesshide", ".sr-only", ".visually-hidden"]:
        for el in a_soup.select(cls):
            el.decompose()
    texto = a_soup.get_text(strip=True)
    for tipo_word in [
        "Página", "Archivo", "Carpeta", "Cuestionario", "Contenido interactivo",
        "Foro", "Tarea", "Etiqueta", "Label", "URL", "H5P",
    ]:
        if texto.endswith(tipo_word):
            texto = texto[: -len(tipo_word)].strip()
    return texto


def _extraer_section_num(sec) -> str:
    sec_id = sec.get("id", "")
    m = None
    if sec_id:
        m = re.search(r"section-(\d+)", sec_id)
    if m:
        return m.group(1)
    data_sec = sec.get("data-sectionid", "")
    if data_sec:
        return str(data_sec)
    return ""


def _quitar_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def _normalizar_header(texto: str) -> str:
    texto = texto.lower().strip()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = texto.strip("_")
    return texto


# ---------------------------------------------------------------------------
# Extracción de sidebar (idéntica a navegador_cdp.py, salvo page_source)
# ---------------------------------------------------------------------------

def extraer_sidebar() -> list[dict]:
    soup = BeautifulSoup(_ultimo_contenido, "lxml")
    items: list[dict] = []

    try:
        # Formato Topics (lista tradicional)
        secciones = soup.select("li.section.main, li.course-section")
        for sec in secciones:
            nombre_el = sec.select_one(".sectionname, .course-section-name, h3")
            nombre = (
                nombre_el.get_text(strip=True)
                if nombre_el
                else sec.get_text(strip=True).split("\n")[0]
            )
            section_num = _extraer_section_num(sec)
            if nombre:
                items.append({
                    "nombre": nombre, "url": "", "tipo": "seccion",
                    "section_num": section_num,
                })

            for act in sec.select("li.activity"):
                link_el = act.select_one("a")
                if not link_el:
                    continue
                href = link_el.get("href", "")
                act_nombre = _limpiar_nombre_actividad(link_el)
                if act_nombre and href:
                    items.append({
                        "nombre": act_nombre, "url": href,
                        "tipo": _detectar_tipo_modulo(href),
                    })

        # Formato Grid (tarjetas)
        grid_sections = soup.select(".grid-section")
        for sec in grid_sections:
            nombre = sec.get("title", "") or sec.get_text(strip=True).split("\n")[0]
            section_num = _extraer_section_num(sec)
            if nombre:
                items.append({
                    "nombre": nombre, "url": "", "tipo": "seccion",
                    "section_num": section_num,
                })

            sec_id = sec.get("id", "")
            if sec_id:
                popup = soup.select_one(
                    f'#{sec_id.replace("section-", "gridpopupsection-")}'
                )
                if popup:
                    for act in popup.select("li.activity"):
                        link_el = act.select_one("a")
                        if not link_el:
                            continue
                        href = link_el.get("href", "")
                        act_nombre = _limpiar_nombre_actividad(link_el)
                        if act_nombre and href:
                            items.append({
                                "nombre": act_nombre, "url": href,
                                "tipo": _detectar_tipo_modulo(href),
                            })

            for act in sec.select("li.activity"):
                link_el = act.select_one("a")
                if not link_el:
                    continue
                href = link_el.get("href", "")
                act_nombre = _limpiar_nombre_actividad(link_el)
                if act_nombre and href:
                    items.append({
                        "nombre": act_nombre, "url": href,
                        "tipo": _detectar_tipo_modulo(href),
                    })
    except Exception:
        pass

    return items


# ---------------------------------------------------------------------------
# Grid popup (degradado — sin click real)
# ---------------------------------------------------------------------------

def abrir_popup_grid_y_obtener_html(nombre_seccion: str) -> str:
    """Busca popup en HTML actual sin click. Fallback: contenido completo."""
    soup = BeautifulSoup(_ultimo_contenido, "lxml")

    for sec in soup.select(".grid-section"):
        titulo = sec.get("title", "") or sec.get_text(strip=True).split("\n")[0]
        if nombre_seccion.lower() in titulo.lower():
            sec_id = sec.get("id", "")
            if not sec_id:
                continue
            popup_id = sec_id.replace("section-", "gridpopupsection-")
            popup = soup.select_one(f"#{popup_id}")
            if popup:
                return str(popup)

    return _ultimo_contenido


# ---------------------------------------------------------------------------
# Extractores de contenido (BS4 en vez de Selenium)
# ---------------------------------------------------------------------------

def extraer_texto_descripcion() -> str:
    soup = BeautifulSoup(_ultimo_contenido, "lxml")
    for selector in [
        ".activity-description",
        "#intro",
        ".content",
        ".description",
        ".summary",
    ]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return ""


def extraer_instrucciones() -> str:
    soup = BeautifulSoup(_ultimo_contenido, "lxml")
    for selector in [
        ".submissioninstructions",
        ".generalbox",
        ".instrucciones",
        ".box.generalbox",
    ]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return ""


def extraer_links_materiales() -> list[str]:
    soup = BeautifulSoup(_ultimo_contenido, "lxml")
    links = []
    try:
        for a in soup.select('a[href*="pluginfile.php"]'):
            href = a.get("href")
            if href:
                links.append(href)
    except Exception:
        pass
    return links


def extraer_criterios() -> str:
    soup = BeautifulSoup(_ultimo_contenido, "lxml")
    for selector in [
        ".gradingform",
        ".criteria",
        ".criterios",
        ".grade-criteria",
    ]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return ""


def extraer_nombre_unidad() -> str:
    soup = BeautifulSoup(_ultimo_contenido, "lxml")
    for selector in ["h1", ".sectionname", ".course-section-name", ".page-header-headings h1"]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return "Unidad"


# ---------------------------------------------------------------------------
# Tablas (idéntico a navegador_cdp.py)
# ---------------------------------------------------------------------------

def _expandir_tabla(tabla) -> list[list[str]]:
    soup = BeautifulSoup(str(tabla), "lxml")
    filas_tr = soup.find_all("tr")

    num_cols = 0
    for tr in filas_tr:
        celdas = tr.find_all(["td", "th"])
        count = sum(int(c.get("colspan", 1)) for c in celdas)
        if count > num_cols:
            num_cols = count

    final_grid: list[list[str]] = []
    rowspan_map: dict[int, tuple[int, str]] = {}
    for tr in filas_tr:
        celdas = tr.find_all(["td", "th"])
        fila = [""] * num_cols
        col_idx = 0
        for celda in celdas:
            texto = celda.get_text(strip=True)
            colspan = int(celda.get("colspan", 1))
            rowspan = int(celda.get("rowspan", 1))
            while col_idx < num_cols and fila[col_idx] != "":
                col_idx += 1
            if col_idx >= num_cols:
                break
            fila[col_idx] = texto
            if rowspan > 1:
                rowspan_map[col_idx] = (rowspan - 1, texto)
            col_idx += colspan
        for c in range(num_cols):
            if c in rowspan_map:
                remaining, texto = rowspan_map[c]
                if fila[c] == "":
                    fila[c] = texto
                rowspan_map[c] = (remaining - 1, texto)
                if remaining <= 1:
                    del rowspan_map[c]
        final_grid.append(fila)

    return final_grid


def _procesar_tabla_bs(tabla) -> list[dict]:
    grid = _expandir_tabla(tabla)
    if len(grid) < 2:
        return []

    max_celdas = 0
    idx_header = 0
    for i, fila in enumerate(grid):
        no_vacias = sum(1 for c in fila if c.strip())
        if no_vacias > max_celdas:
            max_celdas = no_vacias
            idx_header = i

    headers = [_normalizar_header(h) for h in grid[idx_header]]
    resultados = []
    for fila in grid[idx_header + 1 :]:
        if not any(f.strip() for f in fila):
            continue
        resultados.append(dict(zip(headers, fila, strict=False)))

    return resultados


def extraer_filas_tabla(html_content: str, header_text: str) -> list[dict]:
    soup = BeautifulSoup(html_content, "lxml")
    header_norm = _quitar_tildes(header_text).lower()

    # Estrategia 1: header_text dentro de la tabla
    for tabla in soup.find_all("table"):
        texto_tabla = _quitar_tildes(tabla.get_text(separator=" ", strip=True)).lower()
        if header_norm in texto_tabla:
            resultado = _procesar_tabla_bs(tabla)
            if resultado:
                return resultado

    # Estrategia 2: header_text en ancestros (popups/modals Grid)
    for tabla in soup.find_all("table"):
        for ancestor in tabla.parents:
            if ancestor is None or ancestor.name == "body":
                break
            texto_ancestor = _quitar_tildes(
                ancestor.get_text(separator=" ", strip=True)
            ).lower()
            if header_norm in texto_ancestor:
                resultado = _procesar_tabla_bs(tabla)
                if resultado:
                    return resultado

    # Estrategia 3: buscar string con header_text y luego tabla cercana
    for elem in soup.find_all(
        string=re.compile(re.escape(header_text), re.IGNORECASE)
    ):
        for ancestor in [elem.parent] + list(elem.parents):
            if ancestor is None or ancestor.name == "body":
                break
            tabla = ancestor.find("table")
            if tabla:
                resultado = _procesar_tabla_bs(tabla)
                if resultado:
                    return resultado

    return []


# ---------------------------------------------------------------------------
# Solo CDP
# ---------------------------------------------------------------------------

def get_driver():
    raise RuntimeError("get_driver no disponible en modo requests")
