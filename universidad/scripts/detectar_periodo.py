"""
Detección automática de periodo actual basado en fechas de cursos.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

CACHE_DURACION = timedelta(weeks=7)  # 7 semanas


def detectar_periodo(cursos: List[Dict]) -> Dict:
    """
    Determina periodo y bloque actual basado en fechas de cursos.
    
    Args:
        cursos: Lista de cursos con fechas de inicio/fin
        
    Returns:
        Dict con periodo, bloque, fecha_inicio_periodo, fecha_fin_periodo
    """
    if not cursos:
        return {
            "periodo": None,
            "bloque": None,
            "fecha_inicio_periodo": None,
            "fecha_fin_periodo": None
        }
    
    # Obtener fechas de inicio de cursos activos
    fechas_inicio = [c["fecha_inicio"] for c in cursos]
    fecha_min = min(fechas_inicio)
    fecha_max = max([c["fecha_fin"] for c in cursos])
    
    # Determinar periodo (1 o 2) basado en mes de inicio
    mes = fecha_min.month
    if mes <= 6:
        periodo = f"{fecha_min.year}-1"
    else:
        periodo = f"{fecha_min.year}-2"
    
    # Determinar bloque (B1, B2, B3)
    # Bloque 1: primeros 6 semanas del periodo
    # Bloque 2: semanas 7-12
    # Bloque 3: semanas 13+
    dias_desde_inicio = (fecha_max - fecha_min).days
    if dias_desde_inicio <= 42:  # 6 semanas
        bloque = "B1"
    elif dias_desde_inicio <= 84:  # 12 semanas
        bloque = "B2"
    else:
        bloque = "B3"
    
    return {
        "periodo": periodo,
        "bloque": bloque,
        "fecha_inicio_periodo": fecha_min,
        "fecha_fin_periodo": fecha_max
    }


def detectar_cursos_activos(cursos: List[Dict], hoy: Optional[datetime] = None) -> List[Dict]:
    """
    Filtra cursos activos (no terminados).
    
    Args:
        cursos: Lista de cursos
        hoy: Fecha actual (opcional, por defecto hoy)
        
    Returns:
        Lista de cursos activos
    """
    if hoy is None:
        hoy = datetime.now().date()
    
    return [
        c for c in cursos
        if c["fecha_fin"] >= hoy
    ]


def detectar_cursos_terminados(cursos: List[Dict], hoy: Optional[datetime] = None) -> List[Dict]:
    """
    Filtra cursos terminados.
    
    Args:
        cursos: Lista de cursos
        hoy: Fecha actual (opcional, por defecto hoy)
        
    Returns:
        Lista de cursos terminados
    """
    if hoy is None:
        hoy = datetime.now().date()
    
    return [
        c for c in cursos
        if c["fecha_fin"] < hoy
    ]