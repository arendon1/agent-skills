"""
Crear tarea en ClickUp via API.
"""

from typing import List, Optional
from client import get_cliente, iso_a_milisegundos

PRIORIDADES = {
    "urgente": 1,
    "alta": 2,
    "normal": 3,
    "baja": 4
}

def crear_tarea(
    lista_id: str,
    nombre: str,
    descripcion: Optional[str] = None,
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None,
    prioridad: Optional[str] = None,
    markdown_description: bool = True
) -> dict:
    """
    Crea una nueva tarea en ClickUp.
    
    Args:
        lista_id: ID de la lista destino
        nombre: Nombre de la tarea
        descripcion: Descripción (texto o markdown)
        due_date: Fecha en formato ISO 8601 (YYYY-MM-DD)
        tags: Lista de tags a asignar (sin validación, los define el skill orquestador)
        prioridad: "urgente", "alta", "normal", "baja"
        markdown_description: Usar markdown en descripción
        
    Returns:
        Dict con datos de la tarea creada
        
    Raises:
        ValueError si prioridad inválida
        RuntimeError si la API falla
    """
    cliente = get_cliente()
    
    # Validar prioridad
    if prioridad and prioridad not in PRIORIDADES:
        raise ValueError(
            f"Prioridad inválida: '{prioridad}'. "
            f"Valores válidos: {list(PRIORIDADES.keys())}"
        )
    
    # Construir payload
    payload = {"name": nombre}
    
    if descripcion:
        if markdown_description:
            payload["markdown_description"] = descripcion
        else:
            payload["description"] = descripcion
    
    if due_date:
        try:
            payload["due_date"] = iso_a_milisegundos(due_date)
            payload["due_date_time"] = False  # Solo fecha, sin hora
        except ValueError as e:
            raise ValueError(f"Fecha inválida: {e}")
    
    if tags:
        payload["tags"] = tags
    
    if prioridad:
        payload["priority"] = PRIORIDADES[prioridad]
    
    # Hacer request
    response = cliente.post(f"/list/{lista_id}/task", json=payload)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Error creando tarea: {response.status_code} - {response.text}"
        )
    
    return response.json()


def formatear_tarea(tarea: dict) -> str:
    """Formatea tarea para mostrar al usuario."""
    nombre = tarea.get("name", "Sin nombre")
    lista = tarea.get("list", {}).get("name", "Unknown")
    url = tarea.get("url", "")
    due_date = tarea.get("due_date")
    tags = tarea.get("tags", [])
    
    due_date_str = ""
    if due_date:
        from client import milisegundos_a_iso
        due_date_str = f"\n   - Due: {milisegundos_a_iso(due_date)}"
    
    tags_str = ""
    if tags:
        tags_str = f"\n   - Tags: {tags}"
    
    return f"""✅ Tarea creada exitosamente
- Nombre: {nombre}
- Lista: {lista}{due_date_str}{tags_str}
🔗 {url}"""