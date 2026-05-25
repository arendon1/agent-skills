"""
Verifica integridad de archivos locales y links.
"""

import os
from typing import Dict, List

def verificar_integridad(ruta_curso: str) -> Dict:
    """
    Verifica estado de archivos locales vs referencias.
    
    Returns:
        Dict con:
        {
            "archivos_totales": N,
            "archivos_ok": N,
            "links_rotos": N,
            "actividades_sin_detalle": N,
            "problemas": [...]
        }
    """
    problemas = []
    
    # Verificar archivos referenciados en sitemap
    archivos_ok = 0
    archivos_totales = 0
    
    sitemap = leer_sitemap(ruta_curso)
    
    # Verificar archivos de materiales
    for unidad in sitemap.get("unidades", []):
        for material in unidad.get("materiales", []):
            archivos_totales += 1
            if os.path.exists(material["ruta_local"]):
                archivos_ok += 1
            else:
                problemas.append({
                    "tipo": "archivo_faltante",
                    "ruta": material["ruta_local"]
                })
    
    # Verificar actividades con detalle
    actividades_sin_detalle = 0
    for unidad in sitemap.get("unidades", []):
        for actividad in unidad.get("actividades", []):
            if actividad.get("descripcion") == "[DETALLE_NO_ENCONTRADO]":
                actividades_sin_detalle += 1
                problemas.append({
                    "tipo": "actividad_sin_detalle",
                    "nombre": actividad.get("nombre"),
                    "unidad": unidad.get("nombre")
                })
    
    return {
        "archivos_totales": archivos_totales,
        "archivos_ok": archivos_ok,
        "links_rotos": 0,  # Implementar validación de links
        "actividades_sin_detalle": actividades_sin_detalle,
        "problemas": problemas
    }


def leer_sitemap(ruta_local: str) -> Dict:
    """Lee sitemap.json actual."""
    import json
    ruta = os.path.join(ruta_local, "sitemap.json")
    
    if os.path.exists(ruta):
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {"unidades": [], "materiales": [], "actividades": []}