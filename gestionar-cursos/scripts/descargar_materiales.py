"""
Descarga materiales de Moodle aplicando forcedownload=1.
"""

import os
from typing import Optional

from browser_api import obtener_cookies_browser, hacer_get


def descargar_material(url: str, ruta_destino: str) -> bool:
    """
    Descarga material de Moodle.
    
    Args:
        url: URL del material (puede ser pluginfile.php)
        ruta_destino: Ruta local donde guardar el archivo
    
    Returns:
        True si descarga exitosa, False si falló
    """
    # Aplicar forcedownload si es URL de archivo
    url_final = agregar_forcedownload(url)
    
    # Realizar descarga
    try:
        contenido = hacer_get(url_final, headers=generar_headers())
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        
        # Guardar archivo
        with open(ruta_destino, 'wb') as f:
            f.write(contenido)
        
        # Verificar que el archivo no esté vacío
        if os.path.getsize(ruta_destino) > 0:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return False


def agregar_forcedownload(url: str) -> str:
    """
    Añade parámetro forcedownload=1 a URLs de archivos de Moodle.
    """
    if "pluginfile.php" not in url:
        return url
    
    if "?" in url:
        return url + "&forcedownload=1"
    else:
        return url + "?forcedownload=1"


def generar_headers() -> dict:
    """Genera headers para request con cookie de sesión."""
    # Obtener cookies del navegador para autenticación
    cookies = obtener_cookies_browser()
    
    return {
        "User-Agent": "Mozilla/5.0",
        "Cookie": cookies
    }


def es_tipo_descargable(tipo_mime: str) -> bool:
    """Determina si el tipo MIME es descargable."""
    tipos_validos = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats",
        "image/",
        "video/",
        "audio/"
    ]
    
    return any(tipo_mime.startswith(t) for t in tipos_validos)


def descargar_si_existe(url: str, ruta_destino: str) -> bool:
    """
    Wrapper que verifica si el archivo ya existe antes de descargar.
    Evita re-descargar archivos ya existentes.
    """
    if os.path.exists(ruta_destino) and os.path.getsize(ruta_destino) > 0:
        print(f"Archivo ya existe: {ruta_destino}")
        return True
    
    return descargar_material(url, ruta_destino)