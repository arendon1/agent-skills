"""
Extrae cronograma de sesiones sincrónicas con validación de links Teams.
"""

import re
from typing import List, Dict

TEAMS_PATTERN = r'teams\.microsoft\.com/l/meetup-join/'

def es_link_teams_valido(url: str) -> bool:
    """Verifica si el URL es un link directo de reunión Teams."""
    if not url or url == "#" or "pendiente" in url.lower():
        return False
    return bool(re.search(TEAMS_PATTERN, url))


def parsear_sesiones(html_content: str) -> List[Dict]:
    """
    Extrae tabla de cronograma de sesiones sincrónicas.
    
    Columnas de la tabla:
    - Descripción (ej: "Primera sesión")
    - Enlace de Ingreso a las Sesiones
    - Fecha Inicio (dd/mm)
    - Hora Inicio (hh:mm)
    - Enlace de Ingreso a las Grabaciones
    
    Args:
        html_content: HTML crudo de la sección Sesiones Sincrónicas
    
    Returns:
        Lista de diccionarios con datos de cada sesión.
    """
    sesiones = []
    
    # Extraer filas de la tabla de sesiones sincrónicas
    filas = extraer_filas_tabla(html_content, "CRONOGRAMA DE SESIONES SINCRÓNICAS")
    
    for fila in filas:
        descripcion = fila.get("Descripción", "")
        link_teams_raw = fila.get("Enlace de Ingreso a las Sesiones", "")
        link_teams = limpiar_link(link_teams_raw)
        
        fecha_raw = fila.get("Fecha Inicio (dd/mm)", "")
        hora_raw = fila.get("Hora Inicio (hh:mm)", "")
        
        link_grabaciones_raw = fila.get("Enlace de Ingreso a las Grabaciones", "")
        link_grabaciones = limpiar_link(link_grabaciones_raw)
        
        # Validar link Teams
        if not es_link_teams_valido(link_teams):
            link_teams = "[PENDIENTE: Link no seguro o inexistente]"
        
        sesiones.append({
            "descripcion": descripcion,
            "link_teams": link_teams,
            "fecha": fecha_raw,
            "hora": hora_raw,
            "link_grabaciones": link_grabaciones if es_link_teams_valido(link_grabaciones) else "[PENDIENTE]"
        })
    
    return sesiones


def limpiar_link(url: str) -> str:
    """Limpia URL, removiendo parámetros tracking o vacío."""
    if not url or url.strip() in ["", "#", "link", "enlace"]:
        return ""
    
    # Remover espacios
    url = url.strip()
    
    # Remover parámetros de tracking si existen
    # Pero mantener el link real
    return url


def generar_markdown_sesiones(sesiones: List[Dict]) -> str:
    """Genera markdown formateado para archivo SESIONES_SINCRONAS.md."""
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