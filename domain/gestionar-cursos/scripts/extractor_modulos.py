"""
Extractores por tipo de módulo Moodle.

Cada función visita la URL del módulo y extrae datos estructurados
según el tipo de actividad.
"""


from browser_api import get_navegador, get_page_content
from bs4 import BeautifulSoup


def extraer_modulo_page(url: str) -> dict:
    """
    Extrae contenido de un módulo tipo 'page'.

    Returns:
        {"titulo": str, "contenido_html": str, "contenido_texto": str}
    """
    get_navegador()(url)
    soup = BeautifulSoup(get_page_content(), 'lxml')

    # Título
    titulo = soup.select_one('h1, .page-header-headings h1')
    titulo = titulo.get_text(strip=True) if titulo else "Sin título"

    # Contenido principal
    region = soup.select_one('#region-main, .course-content, .activity-content')
    if region:
        contenido_html = str(region)
        contenido_texto = region.get_text(separator='\n', strip=True)
    else:
        contenido_html = ""
        contenido_texto = ""

    return {
        "tipo": "page",
        "url": url,
        "titulo": titulo,
        "contenido_html": contenido_html,
        "contenido_texto": contenido_texto,
    }


def extraer_modulo_quiz(url: str) -> dict:
    """
    Extrae datos de un cuestionario (quiz).

    Returns:
        {"titulo": str, "instrucciones": str, "fecha_apertura": str,
         "fecha_cierre": str, "intentos": str, "tiempo_limite": str,
         "nota_aprobacion": str}
    """
    get_navegador()(url)
    soup = BeautifulSoup(get_page_content(), 'lxml')

    titulo = soup.select_one('h1, .page-header-headings h1')
    titulo = titulo.get_text(strip=True) if titulo else "Sin título"

    # Instrucciones generales
    instrucciones = ""
    content = soup.select_one('#region-main, .activity-content, .quizinfo')
    if content:
        instrucciones = content.get_text(separator='\n', strip=True)

    # Fechas y límites (Moodle los muestra en tablas o spans con clase específica)
    fecha_apertura = ""
    fecha_cierre = ""
    intentos = ""
    tiempo_limite = ""
    nota_aprobacion = ""

    # Buscar en tablas de información del quiz
    for row in soup.select('table.quizinfo tr, .quizinfo tr, tr'):
        cells = row.find_all(['th', 'td'])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)
            if "apertura" in label or "abre" in label or "open" in label:
                fecha_apertura = value
            elif "cierre" in label or "cierra" in label or "close" in label:
                fecha_cierre = value
            elif "intentos" in label or "attempts" in label:
                intentos = value
            elif "tiempo" in label or "time limit" in label:
                tiempo_limite = value
            elif "nota" in label or "grade" in label or "aprob" in label:
                nota_aprobacion = value

    return {
        "tipo": "quiz",
        "url": url,
        "titulo": titulo,
        "instrucciones": instrucciones,
        "fecha_apertura": fecha_apertura,
        "fecha_cierre": fecha_cierre,
        "intentos": intentos,
        "tiempo_limite": tiempo_limite,
        "nota_aprobacion": nota_aprobacion,
    }


def extraer_modulo_hvp(url: str) -> dict:
    """
    Extrae datos de un módulo H5P (interactive content).

    Returns:
        {"titulo": str, "embed_url": str}
    """
    get_navegador()(url)
    soup = BeautifulSoup(get_page_content(), 'lxml')

    titulo = soup.select_one('h1, .page-header-headings h1')
    titulo = titulo.get_text(strip=True) if titulo else "Sin título"

    # Buscar iframe con src que contenga embed.php (H5P)
    iframe = soup.select_one('iframe[src*="embed.php"], iframe[src*="h5p"]')
    embed_url = iframe.get('src', '') if iframe else ""

    # Si no hay iframe, buscar script o meta con la URL
    if not embed_url:
        script = soup.select_one('script:contains("embed.php")')
        if script:
            import re
            match = re.search(r'embed\.php\?id=\d+', script.string or '')
            if match:
                embed_url = match.group(0)

    return {
        "tipo": "hvp",
        "url": url,
        "titulo": titulo,
        "embed_url": embed_url,
    }


def extraer_modulo_folder(url: str) -> dict:
    """
    Extrae lista de archivos de un módulo tipo carpeta (folder).

    Returns:
        {"titulo": str, "archivos": [{"nombre": str, "url": str}]}
    """
    get_navegador()(url)
    soup = BeautifulSoup(get_page_content(), 'lxml')

    titulo = soup.select_one('h1, .page-header-headings h1')
    titulo = titulo.get_text(strip=True) if titulo else "Sin título"

    archivos = []
    for link in soup.select('.folderfiles a, .filemanager a, a[href*="pluginfile.php"]'):  # noqa: E501
        nombre = link.get_text(strip=True)
        href = link.get('href', '')
        if href and nombre:
            archivos.append({"nombre": nombre, "url": href})

    return {
        "tipo": "folder",
        "url": url,
        "titulo": titulo,
        "archivos": archivos,
    }


def extraer_modulo_resource(url: str) -> dict:
    """
    Extrae URL de descarga de un recurso (resource).

    Returns:
        {"titulo": str, "download_url": str, "filename": str}
    """
    get_navegador()(url)
    soup = BeautifulSoup(get_page_content(), 'lxml')

    titulo = soup.select_one('h1, .page-header-headings h1')
    titulo = titulo.get_text(strip=True) if titulo else "Sin título"

    # Buscar link de descarga
    download_link = soup.select_one('a[href*="pluginfile.php"], .resourceworkaround a')
    download_url = download_link.get('href', '') if download_link else url

    # Intentar extraer nombre de archivo de la URL
    filename = ""
    if download_url:
        from urllib.parse import unquote
        parts = download_url.split('/')
        if parts:
            filename = unquote(parts[-1].split('?')[0])

    return {
        "tipo": "resource",
        "url": url,
        "titulo": titulo,
        "download_url": download_url,
        "filename": filename,
    }


def extraer_modulo_assign(url: str) -> dict:
    """
    Extrae datos de una tarea (assign).

    Returns:
        {"titulo": str, "instrucciones": str, "fecha_apertura": str,
         "fecha_cierre": str, "nota_aprobacion": str}
    """
    get_navegador()(url)
    soup = BeautifulSoup(get_page_content(), 'lxml')

    titulo = soup.select_one('h1, .page-header-headings h1')
    titulo = titulo.get_text(strip=True) if titulo else "Sin título"

    instrucciones = ""
    content = soup.select_one('#region-main, .activity-content, .assigninfo')
    if content:
        instrucciones = content.get_text(separator='\n', strip=True)

    fecha_apertura = ""
    fecha_cierre = ""
    nota_aprobacion = ""

    for row in soup.select('table.assigninfo tr, .assigninfo tr, tr'):
        cells = row.find_all(['th', 'td'])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)
            if "apertura" in label or "abre" in label or "open" in label:
                fecha_apertura = value
            elif "cierre" in label or "cierra" in label or "close" in label:
                fecha_cierre = value
            elif "nota" in label or "grade" in label or "aprob" in label:
                nota_aprobacion = value

    return {
        "tipo": "assign",
        "url": url,
        "titulo": titulo,
        "instrucciones": instrucciones,
        "fecha_apertura": fecha_apertura,
        "fecha_cierre": fecha_cierre,
        "nota_aprobacion": nota_aprobacion,
    }


def extraer_modulo_url(url: str) -> dict:
    """
    Extrae datos de un link externo (url).

    Returns:
        {"titulo": str, "external_url": str}
    """
    get_navegador()(url)
    soup = BeautifulSoup(get_page_content(), 'lxml')

    titulo = soup.select_one('h1, .page-header-headings h1')
    titulo = titulo.get_text(strip=True) if titulo else "Sin título"

    external_url = ""
    link = soup.select_one('a[href].urlworkaround, .urlworkaround a, a[href]')
    if link:
        external_url = link.get('href', '')

    return {
        "tipo": "url",
        "url": url,
        "titulo": titulo,
        "external_url": external_url,
    }
