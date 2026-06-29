"""
Compara estado de Moodle vs local y detecta cambios.
"""

import json
import os


def sincronizar_curso(ruta_local: str) -> dict:
    """
    Detecta cambios entre Moodle y carpeta local.

    Returns:
        Dict con estructura:
        {
            "ultima_sync": "timestamp",
            "cambios": [
                {"tipo": "fecha_cambiada", "actividad": "...", "antes": "...", "despues": "..."},
                {"tipo": "nueva", "actividad": "..."},
                {"tipo": "nuevo_material", "recurso": "..."}
            ],
            "grabaciones_nuevas": [...]
        }
    """
    # Leer sitemap actual para comparar
    sitemap_actual = leer_sitemap(ruta_local)

    # Obtener datos frescos de Moodle
    datos_moodle = extraer_datos_moodle(ruta_local)

    cambios = []
    grabaciones_nuevas = []

    # Comparar fechas de PGA
    pga_local = sitemap_actual.get("pga", [])
    pga_moodle = datos_moodle.get("pga", [])

    for i, actividad in enumerate(pga_moodle):
        if i < len(pga_local):
            if actividad["fecha_fin"] != pga_local[i]["fecha_fin"]:
                cambios.append({
                    "tipo": "fecha_cambiada",
                    "actividad": actividad["actividad"],
                    "antes": pga_local[i]["fecha_fin"],
                    "despues": actividad["fecha_fin"]
                })
        else:
            # Nueva actividad
            cambios.append({
                "tipo": "nueva",
                "actividad": actividad["actividad"]
            })

    # Verificar links de grabaciones nuevas
    sesiones_moodle = datos_moodle.get("sesiones", [])
    sesiones_local = sitemap_actual.get("sesiones", [])

    for i, sesion in enumerate(sesiones_moodle):
        if (sesion.get("link_grabaciones")
                and sesion["link_grabaciones"] != "[PENDIENTE]"
                and (i >= len(sesiones_local)
                     or not sesiones_local[i].get("link_grabaciones"))):
            grabaciones_nuevas.append({
                "descripcion": sesion["descripcion"],
                "link": sesion["link_grabaciones"],
                "fecha": sesion["fecha"]
            })

    # Guardar nuevo estado
    guardar_sitemap(ruta_local, datos_moodle)

    return {
        "ultima_sync": get_timestamp(),
        "cambios": cambios,
        "grabaciones_nuevas": grabaciones_nuevas
    }


def leer_sitemap(ruta_local: str) -> dict:
    """Lee sitemap.json actual."""
    ruta = os.path.join(ruta_local, "sitemap.json")

    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)

    return {"pga": [], "sesiones": [], "secciones": []}


def guardar_sitemap(ruta_local: str, datos: dict):
    """Guarda estado actualizado en sitemap.json."""
    ruta = os.path.join(ruta_local, "sitemap.json")

    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


def extraer_datos_moodle(ruta_local: str) -> dict:
    """
    Extrae datos frescos de Moodle para el curso.
    Requiere el URL del curso en AGENTS.md
    """
    # Leer URL del curso
    agents_path = os.path.join(ruta_local, "AGENTS.md")
    with open(agents_path, encoding='utf-8') as f:
        content = f.read()

    # Extraer Moodle URL
    import re
    match = re.search(r'MOODLE_URL.*?(https://[^\s]+)', content)
    if not match:
        raise ValueError("No se encontró MOODLE_URL en AGENTS.md")

    # Aquí se debería navegar a Moodle y extraer los datos
    # Esto es un stub - implementar con navegación real
    return {
        "pga": [],
        "sesiones": [],
        "unidades": [],
        "secciones": []
    }


def get_timestamp() -> str:
    """Obtiene timestamp actual en formato ISO."""
    from datetime import datetime
    return datetime.now().isoformat()
