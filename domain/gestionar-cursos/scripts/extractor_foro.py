"""
Extractor de foros de Moodle.

Extrae discusiones de primer nivel (root) iniciadas por el profesor del curso.
Solo el contenido original de la discusión, no las respuestas.
"""


from browser_api import get_navegador, get_page_content
from bs4 import BeautifulSoup


def extraer_nombre_profesor(html_pagina: str) -> str | None:
    """
    Extrae el nombre del profesor del HTML de la página del curso.
    Busca en tablas, encabezados y texto que contenga "Nombre Completo" o similar.

    Args:
        html_pagina: HTML de la página principal del curso o de 'Conoce tu profesor'.

    Returns:
        Nombre del profesor o None si no se encuentra.
    """
    import re
    soup = BeautifulSoup(html_pagina, 'lxml')

    # Estrategia 1: buscar tabla con "Nombre Completo" y extraer el valor
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            celdas = row.find_all(['td', 'th'])
            for i, cell in enumerate(celdas):
                texto_celda = cell.get_text(strip=True).lower()
                if 'nombre completo' in texto_celda or 'nombre' in texto_celda:
                    if i + 1 < len(celdas):
                        nombre = celdas[i + 1].get_text(strip=True)
                        if nombre:
                            return _limpiar_nombre_profesor(nombre)
                    # Si está en la misma celda ( separado por : )
                    m = re.search(r'[Nn]ombre\s*[Cc]ompleto[:\s]+([A-Z][a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+)', cell.get_text(strip=True))
                    if m:
                        return _limpiar_nombre_profesor(m.group(1).strip())

    # Estrategia 2: buscar en encabezados
    for heading in soup.select('h1, h2, h3, .page-header-headings h1'):
        texto = heading.get_text(strip=True)
        if texto and texto not in ['Conoce tu profesor', 'Área personal', 'Curso'] and re.search(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4}$', texto):
            return _limpiar_nombre_profesor(texto)

    # Estrategia 3: buscar en párrafos/divs que contengan "profesor" o "docente"
    for p in soup.select('p, div'):
        texto = p.get_text(strip=True)
        if 'profesor' in texto.lower() or 'docente' in texto.lower():
            # Buscar nombre completo en el mismo elemento
            m = re.search(r'([A-Z][a-zA-ZáéíóúÁÉÍÓÚñÑ]+(?:\s+[A-Z][a-zA-ZáéíóúÁÉÍÓÚñÑ]+){1,4})', texto)
            if m:
                candidato = m.group(1)
                if len(candidato) > 10:
                    return _limpiar_nombre_profesor(candidato)

    return None


def _limpiar_nombre_profesor(nombre: str) -> str:
    """Elimina prefijos comunes y corta en la primera palabra no-nombre."""
    import re
    # Eliminar prefijos
    for prefijo in [
        r'^Presentaci\u00f3n\s+',
        r'^Prof\.?\s+',
        r'^Docente\s+',
        r'^Profesor(a)?\s+',
    ]:
        nombre = re.sub(prefijo, '', nombre, flags=re.IGNORECASE)
    # Cortar en palabras que indican título/profesión (no parte del nombre)
    cortes = ['Profesional', 'Ingeniero', 'Ingeniera', 'Magister', 'Doctor', 'Doctora',
              'Master', 'Máster', 'Licenciado', 'Licenciada', 'Tecnólogo', 'Tecnóloga',
              'Especialista', 'Técnico', 'Técnica']
    for corte in cortes:
        idx = nombre.find(corte)
        if idx != -1:
            nombre = nombre[:idx].strip()
            break
    # Cortar en la primera letra minúscula (heurística: nombres propios no tienen minúsculas en medio)
    m = re.search(r'^([A-Z][a-zA-ZáéíóúÁÉÍÓÚñÑ]+(?:\s+[A-Z][a-zA-ZáéíóúÁÉÍÓÚñÑ]+){1,4})', nombre)
    if m:
        return m.group(1).strip()
    return nombre.strip()


def _extraer_autor_y_fecha(autor_el) -> tuple[str, str]:
    """Separa nombre del autor de la fecha en celdas de foro."""
    import re

    from bs4 import BeautifulSoup

    # Estrategia 1: buscar elemento de fecha separado dentro de la celda
    fecha_el = autor_el.select_one('time, .date, .time, .lastpost, span[title]')
    if fecha_el:
        fecha = fecha_el.get_text(strip=True)
        temp = BeautifulSoup(str(autor_el), 'lxml')
        for sel in ['time', '.date', '.time', '.lastpost']:
            for el in temp.select(sel):
                el.decompose()
        autor = temp.get_text(strip=True)
        return autor, fecha

    # Estrategia 2: regex para separar fecha al final del texto
    texto = autor_el.get_text(strip=True)
    m = re.search(
        r'(.*?)\s+(\d{1,2}\s+[a-zA-Z]{3,}\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-\d{1,2}-\d{4})$',
        texto
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()

    return texto, ""


def extraer_discusiones_foro(url_foro: str, nombre_profesor: str) -> list[dict]:
    """
    Navega al foro, lista las discusiones y extrae solo las del profesor.

    Args:
        url_foro: URL del foro en Moodle.
        nombre_profesor: Nombre completo del profesor para filtrar.

    Returns:
        Lista de dicts: {"titulo": str, "autor": str, "fecha": str, "contenido": str}
    """
    get_navegador()(url_foro)
    soup = BeautifulSoup(get_page_content(), 'lxml')

    discusiones = []

    # Moodle muestra discusiones en una tabla con clase 'forumheaderlist' o similar
    # Cada fila tiene: título, autor, réplicas, último mensaje
    filas = soup.select('table.forumheaderlist tr, .discussion-list tr, [data-region="discussion-list"] tr')

    for fila in filas:
        celdas = fila.find_all(['td', 'th'])
        if len(celdas) < 3:
            continue

        # Extraer datos de la fila
        titulo_el = fila.select_one('a[href*="/mod/forum/discuss.php"], .discussion-title a')
        autor_el = fila.select_one('.author, .starter, td:nth-child(3)')

        if not titulo_el or not autor_el:
            continue

        titulo = titulo_el.get_text(strip=True)
        url_disc = titulo_el.get('href', '')
        autor, fecha = _extraer_autor_y_fecha(autor_el)

        # Filtrar: solo discusiones del profesor
        if not _es_autor_profesor(autor, nombre_profesor):
            continue

        # Navegar a la discusión y extraer contenido del primer post
        contenido = _extraer_primer_post(url_disc)

        if contenido:
            discusiones.append({
                "titulo": titulo,
                "autor": autor,
                "fecha": fecha,
                "url": url_disc,
                "contenido": contenido,
            })

    return discusiones


def _es_autor_profesor(autor_lista: str, nombre_profesor: str) -> bool:
    """
    Compara el nombre del autor en la lista con el nombre del profesor.
    Usa matching parcial porque Moodle puede mostrar nombres ligeramente diferentes.
    """
    if not autor_lista or not nombre_profesor:
        return False

    autor_norm = _normalizar_nombre(autor_lista)
    prof_norm = _normalizar_nombre(nombre_profesor)

    # Matching exacto o contenido parcial
    return prof_norm in autor_norm or autor_norm in prof_norm


def _normalizar_nombre(nombre: str) -> str:
    """Normaliza nombre para comparación."""
    return nombre.lower().strip().replace("  ", " ")


def _extraer_primer_post(url_discusion: str) -> str | None:
    """
    Navega a la página de la discusión y extrae solo el contenido del primer post.
    Ignora replies.
    """
    try:
        get_navegador()(url_discusion)
        soup = BeautifulSoup(get_page_content(), 'lxml')

        # Moodle tiene varios formatos de foro
        # Formato moderno: div.firstpost, article.forum-post-container
        primer_post = soup.select_one('.firstpost, article.forum-post-container, #p1')

        if not primer_post:
            # Fallbacks adicionales
            primer_post = soup.select_one('.forumpost, [data-region="post-content"]')

        if not primer_post:
            return None

        # Extraer contenido del post
        contenido_el = primer_post.select_one('.post-message, .content, .post-content, [data-region="post-content"]')
        if contenido_el:
            return contenido_el.get_text(separator='\n', strip=True)

        # Fallback: texto del post completo
        return primer_post.get_text(separator='\n', strip=True)

    except Exception as e:
        print(f"[WARN] Error extrayendo post de {url_discusion}: {e}")
        return None
