"""
Actualizar tarea existente en ClickUp via API.
"""

from typing import Optional, List
from client import get_cliente, iso_a_milisegundos

def actualizar_tarea(
    task_id: str,
    nombre: Optional[str] = None,
    descripcion: Optional[str] = None,
    due_date: Optional[str] = None,
    prioridad: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
    markdown_description: bool = True
) -> dict:
    """
    Actualiza campos de una tarea existente.
    
    Args:
        task_id: ID de la tarea a actualizar
        nombre: Nuevo nombre (opcional)
        descripcion: Nueva descripción (opcional)
        due_date: Nueva fecha en ISO 8601 (opcional)
        prioridad: Nueva prioridad (opcional)
        tags: Nuevos tags (reemplaza los actuales)
        status: Nuevo status (ej: "in progress", "complete")
        
    Returns:
        Dict con datos de la tarea actualizada
        
    Note: Custom fields no se pueden actualizar con PUT /tasks/{task_id}.
    Para custom fields, usar el endpoint específico.
    """
    cliente = get_cliente()
    
    # Construir payload con solo campos a actualizar
    payload = {}
    
    if nombre is not None:
        payload["name"] = nombre
    
    if descripcion is not None:
        if markdown_description:
            payload["markdown_description"] = descripcion
        else:
            payload["description"] = descripcion
    
    if due_date is not None:
        try:
            payload["due_date"] = iso_a_milisegundos(due_date)
        except ValueError as e:
            raise ValueError(f"Fecha inválida: {e}")
    
    if prioridad is not None:
        PRIORIDADES = {"urgent": 1, "high": 2, "normal": 3, "low": 4}
        if prioridad not in PRIORIDADES:
            raise ValueError(f"Prioridad inválida: {prioridad}")
        payload["priority"] = PRIORIDADES[prioridad]
    
    if tags is not None:
        payload["tags"] = tags
    
    if status is not None:
        payload["status"] = status
    
    if not payload:
        raise ValueError("No se proporcionaron campos a actualizar")
    
    # Hacer request
    response = cliente.put(f"/task/{task_id}", json=payload)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Error actualizando tarea: {response.status_code} - {response.text}"
        )
    
    return response.json()