"""
Extrae cronograma de sesiones sincrónicas con validación de links Teams.

Parsea directamente la tabla HTML para obtener hrefs de enlaces,
no solo el texto de las celdas.
"""

import re

from bs4 import BeautifulSoup

TEAMS_PATTERN = r'teams\.microsoft\.com/(?:l/meetup-join|meet)/'


def es_link_teams_valido(url: str) -> bool:
    """Verifica si el URL es un link directo de reunión Teams."""
    if not url or url == "#" or "pendiente" in url.lower():
        return False
    return bool(re.search(TEAMS_PATTERN, url))


def _quitar_tildes(texto: str) -> str:
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


def _texto_celda(celda) -> str:
    """Extrae texto plano de una celda, ignorando tags internos."""
    return celda.get_text(separator=' ', strip=True)


def _primer_href(celda) -> str:
    """Devuelve el href del primer <a> dentro de la celda, o texto si no hay link."""
    a = celda.find('a')
    if a:
        href = a.get('href', '').strip()
        if href and href != '#':
            return href
    return _texto_celda(celda)


def parsear_sesiones(html_content: str) -> list[dict]:
    """
    Extrae tabla de cronograma de sesiones sincrónicas del HTML.

    Busca la tabla que contiene "CRONOGRAMA DE SESIONES SINCRÓNICAS" y extrae:
    - Descripción (texto de la 1ra columna)
    - Link Teams (href del <a> en la 2da columna)
    - Fecha (texto de la 3ra columna)
    - Hora (texto de la 4ta columna)
    - Link Grabaciones (href del <a> en la 5ta columna)
    """
    soup = BeautifulSoup(html_content, 'lxml')
    sesiones = []

    for tabla in soup.find_all('table'):
        texto_tabla = _quitar_tildes(tabla.get_text(separator=' ', strip=True)).lower()
        if 'cronograma de sesiones sincronicas' not in texto_tabla:
            continue

        filas_tr = tabla.find_all('tr')

        # Encontrar fila de headers de columna (la que tiene "Descripción" + "Enlace")
        idx_header = -1
        for i, tr in enumerate(filas_tr):
            celdas = tr.find_all(['td', 'th'])
            if len(celdas) >= 5:
                header_text = _quitar_tildes(' '.join(_texto_celda(c) for c in celdas)).lower()
                if 'descripcion' in header_text and 'enlace' in header_text:
                    idx_header = i
                    break

        if idx_header == -1:
            continue

        # Procesar filas de datos después del header
        for tr in filas_tr[idx_header + 1:]:
            celdas = tr.find_all(['td', 'th'])
            if len(celdas) < 5:
                continue

            descripcion = _texto_celda(celdas[0])
            link_teams_raw = _primer_href(celdas[1])
            fecha = _texto_celda(celdas[2])
            hora = _texto_celda(celdas[3])
            link_grab_raw = _primer_href(celdas[4])

            link_teams = link_teams_raw if es_link_teams_valido(link_teams_raw) else "[PENDIENTE: Link no seguro o inexistente]"
            link_grabaciones = link_grab_raw if link_grab_raw and link_grab_raw != '#' else "[PENDIENTE]"

            sesiones.append({
                "descripcion": descripcion,
                "link_teams": link_teams,
                "fecha": fecha,
                "hora": hora,
                "link_grabaciones": link_grabaciones,
            })

        break  # Solo la primera tabla que coincida

    return sesiones


def generar_markdown_sesiones(sesiones: list[dict]) -> str:
    """Genera markdown formateado para insertar en AGENTS.md o SESIONES_SINCRONAS.md."""
    lines = [
        "# Sesiones Sincrónicas",
        "",
        "| Descripción | Link Teams | Fecha | Hora | Grabaciones |",
        "|-------------|------------|-------|------|--------------|"
    ]

    for sesion in sesiones:
        lines.append(
            f"| {sesion['descripcion']} | {sesion['link_teams']} | "
            f"{sesion['fecha']} | {sesion['hora']} | {sesion['link_grabaciones']} |"
        )

    lines.append("")
    lines.append("**Nota:** Para ingresar a las sesiones debe iniciar sesión en Office 365 institucional.")

    return "\n".join(lines)
