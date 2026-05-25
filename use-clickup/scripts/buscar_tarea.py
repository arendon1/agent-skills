"""
Buscar tareas en ClickUp usando diversos filtros.
"""

from typing import List, Optional, Dict
from difflib import SequenceMatcher
from client import get_cliente, milisegundos_a_iso

def calcular_similitud(a: str, b: str) -> float:
    """Calcula ratio de similitud entre dos strings (0.0 a 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def buscar_tareas(
    nombre: Optional[str] = None,
    tag: Optional[str] = None,
    lista_id: Optional[str] = None,
    espacio_id: Optional[str] = None,
    limite: int = 50
) -> List[Dict]:
    """
    Busca tareas con filtros opcionales.
    
    Args:
        nombre: Nombre (o parte) a buscar
        tag: Filtrar por tag
        lista_id: Filtrar por lista específica
        espacio_id: Filtrar por espacio
        limite: Máximo de tareas a retornar (default 50)
        
    Returns:
        Lista de dicts con tasks matching
    """
    cliente = get_cliente()
    
    # Construir query params
    params = {"limit": limite}
    
    # ClickUp API tiene endpoint /tasks pero con filtros limitados
    # Para búsqueda por nombre, necesitamos get tasks y filtrar
    
    if lista_id:
        endpoint = f"/list/{lista_id}/task"
    elif espacio_id:
        # Tasks de espacio requieren folder/list intermediario
        raise ValueError(
            "Para filtrar por espacio, especificar lista_id o folder_id"
        )
    else:
        # Tasks del workspace (puede ser muy extenso)
        endpoint = "/team/tasks"
        params["include_closed"] = "true"
    
    # Obtener tasks
    response = cliente.get(endpoint, params=params)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Error buscando tareas: {response.status_code} - {response.text}"
        )
    
    data = response.json()
    tasks = data.get("tasks", [])
    
    # Filtrar resultados
    resultados = []
    
    for task in tasks:
        # Filtrar por nombre si especificado
        if nombre:
            similitud = calcular_similitud(nombre, task.get("name", ""))
            if similitud < 0.6:  # Threshold de fuzzy match
                continue
            task["_similitud"] = similitud
        
        # Filtrar por tag si especificado
        if tag:
            task_tags = task.get("tags", [])
            if tag not in task_tags:
                continue
        
        resultados.append(task)
    
    # Ordenar por similitud si aplicable
    if nombre:
        resultados.sort(key=lambda t: t.get("_similitud", 0), reverse=True)
    
    return resultados


def formatear_resultados(tasks: List[Dict]) -> str:
    """Formatea lista de tasks para mostrar al usuario."""
    if not tasks:
        return "🔍 No se encontraron tareas"
    
    lineas = [f"🔍 {len(tasks)} tarea(s) encontrada(s):\n"]
    
    for i, task in enumerate(tasks, 1):
        nombre = task.get("name", "Sin nombre")
        similitud = task.get("_similitud")
        status = task.get("status", {}).get("status", "unknown")
        due_date = task.get("due_date")
        tags = task.get("tags", [])
        url = task.get("url", "")
        
        # Similitud si se buscó por nombre
        match_info = ""
        if similitud is not None:
            match_info = f" ({int(similitud * 100)}% match)"
        
        due_str = ""
        if due_date:
            due_str = f" | Due: {milisegundos_a_iso(due_date)}"
        
        tags_str = ""
        if tags:
            tags_str = f" | Tags: {tags}"
        
        lineas.append(
            f"{i}. {nombre}{match_info}\n"
            f"   Status: {status}{due_str}{tags_str}\n"
            f"   🔗 {url}\n"
        )
    
    return "\n".join(lineas)