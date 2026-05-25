"""
Crear lista en ClickUp via API.
"""

from client import get_cliente

def crear_lista(
    folder_id: str,
    nombre: str,
    contenido: str = ""
) -> dict:
    """
    Crea una nueva lista en un folder.
    
    Args:
        folder_id: ID del folder padre
        nombre: Nombre de la lista
        contenido: Descripción inicial (opcional)
        
    Returns:
        Dict con datos de la lista creada
    """
    cliente = get_cliente()
    
    payload = {
        "name": nombre,
        "folder_id": folder_id,
        "content": contenido
    }
    
    response = cliente.post("/list", json=payload)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Error creando lista: {response.status_code} - {response.text}"
        )
    
    return response.json()


def formatear_lista(lista: dict) -> str:
    """Formatea lista para mostrar al usuario."""
    nombre = lista.get("name", "Sin nombre")
    folder = lista.get("folder", {}).get("name", "Unknown")
    url = lista.get("url", "")
    task_count = lista.get("task_count", 0)
    
    return f"""✅ Lista creada exitosamente
- Nombre: {nombre}
- Folder: {folder}
- Tasks: {task_count}
🔗 {url}"""