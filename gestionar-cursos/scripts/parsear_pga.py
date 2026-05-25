"""
Extrae y normaliza la tabla DO-FR-66 Plan de Gestión Académica.
"""

from datetime import datetime
from typing import List, Dict

def normalizar_fecha(fecha_str: str) -> str:
    """
    Convierte fecha de formato DD/M/YYYY a YYYY-MM-DD (ISO 8601).
    
    Args:
        fecha_str: String con fecha ej: "26/1/2026"
    
    Returns:
        Fecha en formato ISO 8601 ej: "2026-01-26"
    """
    try:
        # Parsear formato DD/M/YYYY
        fecha = datetime.strptime(fecha_str.strip(), "%d/%m/%Y")
        return fecha.strftime("%Y-%m-%d")
    except ValueError:
        # Si no funciona, intentar otros formatos comunes
        for fmt in ["%d/%m/%y", "%d-%m-%Y", "%d-%m-%y"]:
            try:
                fecha = datetime.strptime(fecha_str.strip(), fmt)
                return fecha.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # Si ningún formato funciona, retornar original con warning
        return fecha_str


def parsear_pga(html_content: str) -> List[Dict]:
    """
    Extrae tabla DO-FR-66 del HTML de Introducción.
    
    La tabla tiene columnas:
    - Semanas
    - Unidad(es)
    - Actividad(es)
    - Valor en Porcentaje
    - Fecha Inicio
    - Fecha Fin
    
    Args:
        html_content: HTML crudo de la sección Introducción
    
    Returns:
        Lista de diccionarios con datos de cada actividad.
        Actividades compuestas se split en filas individuales.
    """
    actividades = []
    
    # Buscar tabla bajo encabezado "DO-FR-66"
    # El HTML de Moodle tiene estructura de tabla específica
    
    # Extracción ejemplo - ajustar según HTML real de Uniremington
    filas = extraer_filas_tabla(html_content, "DO-FR-66")
    
    for fila in filas:
        semanas = fila.get("Semanas", "")
        unidad = fila.get("Unidad(es)", "")
        actividad_raw = fila.get("Actividad(es)", "")
        valor_raw = fila.get("Valor en Porcentaje", "")
        fecha_inicio = normalizar_fecha(fila.get("Fecha Inicio", ""))
        fecha_fin = normalizar_fecha(fila.get("Fecha Fin", ""))
        
        # Split actividades compuestas (separadas por <br> o similar)
        actividades_list = split_actividades_compuestas(actividad_raw)
        valores_list = split_valores_compuestos(valor_raw)
        
        # Crear fila por cada actividad
        for i, act in enumerate(actividades_list):
            # Limpiar nombre de actividad
            act_nombre = limpiar_nombre_actividad(act)
            
            # Obtener valor correspondiente (o usar último si no hay match)
            valor = valores_list[i] if i < len(valores_list) else valores_list[-1] if valores_list else ""
            
            actividades.append({
                "semana": semanas,
                "unidad": unidad,
                "actividad": act_nombre,
                "valor": valor,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "fecha_inicio_raw": fila.get("Fecha Inicio", ""),
                "fecha_fin_raw": fila.get("Fecha Fin", "")
            })
    
    return actividades


def split_actividades_compuestas(texto: str) -> List[str]:
    """Separa actividades unidas por <br> o ' + '."""
    # Moodle une actividades con <br> en celdas compuestas
    partes = texto.replace("<br>", "+").split("+")
    return [p.strip() for p in partes if p.strip()]


def split_valores_compuestos(texto: str) -> List[str]:
    """Separa valores de porcentaje unidos por <br> o ' + '."""
    partes = texto.replace("<br>", "+").split("+")
    return [p.strip() for p in partes if p.strip()]


def limpiar_nombre_actividad(nombre: str) -> str:
    """Limpia nombre de actividad, removiendo espacios extra y tags HTML."""
    import re
    # Remover tags HTML si existen
    nombre = re.sub(r'<[^>]+>', '', nombre)
    # Limpiar espacios
    nombre = ' '.join(nombre.split())
    return nombre.strip()


def generar_markdown_pga(actividades: List[Dict]) -> str:
    """Genera markdown formateado para archivo PGA.md."""
    lines = [
        "# Plan de Gestión Académica",
        "",
        "| Semana | Unidad | Actividad | Valor | Fecha Inicio | Fecha Fin |",
        "|--------|--------|-----------|-------|--------------|-----------|"
    ]
    
    for act in actividades:
        fecha_inicio = f"{act['fecha_inicio_raw']} ({act['fecha_inicio']})"
        fecha_fin = f"{act['fecha_fin_raw']} ({act['fecha_fin']})"
        
        lines.append(
            f"| {act['semana']} | {act['unidad']} | {act['actividad']} | "
            f"{act['valor']} | {fecha_inicio} | {fecha_fin} |"
        )
    
    return "\n".join(lines)