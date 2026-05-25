"""
Listar listas disponibles en folder o space.
"""

from typing import Optional
from client import get_cliente

def ver_listas(
    folder_id: Optional[str] = None,
    space_id: Optional[str] = None
) -> list:
    """
    Obtiene listas de un folder o space.
    
    Args:
        folder_id: ID del folder (prioridad sobre space_id)
        space_id: ID del space
        
    Returns:
        Lista de diccionarios con datos de listas
        
    Raises:
        ValueError si no se provee folder_id ni space_id
    """
    cliente = get_cliente()
    
    if folder_id:
        # Listas en folder específico
        endpoint = f"/folder/{folder_id}/list"
    elif space_id:
        # Listas directas en space (no en folders)
        endpoint = f"/space/{space_id}/list"
    else:
        raise ValueError(
            "Debes especificar folder_id o space_id"
        )
    
    response = cliente.get(endpoint)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Error obteniendo listas: {response.status_code} - {response.text}"
        )
    
    data = response.json()
    return data.get("lists", [])


def formatear_listas(listas: list, contexto: str = "") -> str:
    """Formatea listas para mostrar al usuario."""
    if not listas:
        return f"📋 No hay listas en {contexto}"
    
    lineas = [f"📋 Listas{contexto}:\n"]
    
    for i, lista in enumerate(listas, 1):
        nombre = lista.get("name", "Sin nombre")
        task_count = lista.get("task_count", 0)
        status = lista.get("status", {})
        # Status puede ser None o dict
        if status and isinstance(status, dict):
            status_name = status.get("status", "active")
        else:
            status_name = "active"
        
        url = lista.get("url", "")
        
        lineas.append(
            f"{i}. {nombre}\n"
            f"   Tasks: {task_count} | Status: {status_name}\n"
            f"   🔗 {url}\n"
        )
    
    return "\n".join(lineas)