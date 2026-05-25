"""
Navega unidad de curso, expande menús desplegables,
busca actividades del PGA y extrae detalles completos.
"""

from typing import Dict, Optional, List
from difflib import SequenceMatcher

def extraer_unidad(url_unidad: str, actividades_pga: List[str]) -> Dict:
    """
    Extrae información completa de una unidad.
    
    1. Navega a la URL de la unidad
    2. Expande todos los menús desplegables del sidebar
    3. Por cada actividad del PGA, busca coincidencia en la unidad
    4. Extrae: descripción, instrucciones, materiales, criterios
    
    Args:
        url_unidad: URL de la unidad en Moodle
        actividades_pga: Lista de nombres de actividades del PGA
    
    Returns:
        Dict con estructura:
        {
            "nombre": "Unidad 1",
            "actividades": [
                {
                    "nombre": "Prueba Inicial",
                    "descripcion": "...",
                    "instrucciones": "...",
                    "materiales": ["link1", "link2"],
                    "encontrada": True/False
                }
            ]
        }
    """
    navegador = get_navegador()
    
    # Navegar a la unidad
    navegador(url_unidad)
    
    # Expandir todos los menús desplegables del sidebar
    expandir_menus_desplegables()
    
    # Extraer todas las secciones visibles
    sidebar_items = extraer_sidebar()
    
    actividades_encontradas = []
    
    for actividad_nombre in actividades_pga:
        detalle = buscar_actividad_en_sidebar(sidebar_items, actividad_nombre)
        
        if detalle:
            # Extraer información completa de la actividad
            detalle_completo = extraer_detalle_actividad(detalle["url"])
            actividades_encontradas.append({
                "nombre": actividad_nombre,
                **detalle_completo,
                "encontrada": True
            })
        else:
            # No encontrada - marcar pero no fallar
            actividades_encontradas.append({
                "nombre": actividad_nombre,
                "descripcion": "[DETALLE_NO_ENCONTRADO]",
                "encontrada": False
            })
    
    return {
        "nombre": extraer_nombre_unidad(),
        "actividades": actividades_encontradas
    }


def similar(a: str, b: str, threshold: float = 0.7) -> bool:
    """Determina si dos strings son similares usando ratio de coincidencias."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def buscar_actividad_en_sidebar(sidebar_items: List[Dict], nombre_buscado: str) -> Optional[Dict]:
    """
    Busca actividad en sidebar usando fuzzy matching.
    
    Moodle a veces muestra nombres ligeramente diferentes.
    """
    nombre_buscado_normalizado = normalizar_nombre(nombre_buscado)
    
    for item in sidebar_items:
        nombre_item_normalizado = normalizar_nombre(item.get("nombre", ""))
        
        if nombre_buscado_normalizado in nombre_item_normalizado:
            return item
        
        if similar(nombre_buscado_normalizado, nombre_item_normalizado):
            return item
    
    return None


def normalizar_nombre(nombre: str) -> str:
    """Normaliza nombre de actividad para comparación."""
    import re
    # Remover tags HTML
    nombre = re.sub(r'<[^>]+>', '', nombre)
    # Lowercase y strip
    nombre = nombre.lower().strip()
    # Remover caracteres especiales excepto espacios y guiones
    nombre = re.sub(r'[^\w\s-]', '', nombre)
    return nombre


def expandir_menus_desplegables():
    """
    Expande todos los menús desplegables del sidebar de Moodle.
    Las actividades pueden estar ocultas dentro de estos menús.
    """
    # Los menús de Moodle típicamente tienen clase "collapside" o similar
    # Click en elementos con aria-expanded="false" o similares
    
    while True:
        menus_cerrados = encontrar_menus_cerrados()
        if not menus_cerrados:
            break
        
        for menu in menus_cerrados:
            click(menu)
            esperar_carga()


def extraer_sidebar() -> List[Dict]:
    """
    Extrae todos los items del sidebar de la unidad.
    
    Returns:
        Lista de dicts con {nombre, url, tipo}
    """
    # Implementar extracción de sidebar desde HTML
    # Buscar estructura de lista en sidebar
    pass


def extraer_detalle_actividad(url_actividad: str) -> Dict:
    """
    Navega a la página de detalle de una actividad y extrae:
    - Descripción completa
    - Instrucciones de entrega
    - Materiales adjuntos
    - Criterios de evaluación
    
    Returns:
        Dict con datos extraídos
    """
    navegador = get_navegador()
    navegador(url_actividad)
    
    # Extraer elementos de la página
    descripcion = extraer_texto_descripcion()
    instrucciones = extraer_instrucciones()
    materiales = extraer_links_materiales()
    criterios = extraer_criterios()
    
    return {
        "descripcion": descripcion,
        "instrucciones": instrucciones,
        "materiales": materiales,
        "criterios": criterios,
        "url": url_actividad
    }