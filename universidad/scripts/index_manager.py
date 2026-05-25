"""
Gestión del índice local .universidad_index.json.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

CACHE_DURACION = timedelta(weeks=7)  # 7 semanas


def cargar_index(ruta_index: str = ".universidad_index.json") -> Optional[Dict]:
    """
    Carga el índice local si existe y no ha expirado.
    
    Args:
        ruta_index: Ruta al archivo de índice
        
    Returns:
        Dict con el índice o None si no existe/expiró
    """
    if not os.path.exists(ruta_index):
        return None
    
    try:
        with open(ruta_index, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def guardar_index(index: Dict, ruta_index: str = ".universidad_index.json"):
    """
    Guarda el índice local.
    
    Args:
        index: Dict con el índice
        ruta_index: Ruta al archivo de índice
    """
    with open(ruta_index, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def validar_cache(index: Optional[Dict]) -> bool:
    """
    Verifica si el cache es válido (no ha expirado).
    
    Args:
        index: Dict del índice
        
    Returns:
        True si válido, False si expiró o no existe
    """
    if index is None:
        return False
    
    cache_valid_until = index.get("cache_valid_until")
    if not cache_valid_until:
        return False
    
    try:
        fecha_valida = datetime.fromisoformat(cache_valid_until)
        return datetime.now() < fecha_valida
    except ValueError:
        return False