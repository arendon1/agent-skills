"""
Gestión de sesión Moodle: exporta cookies de Selenium → requests.Session
para scraping rápido sin navegador.
"""

import json
from pathlib import Path

import requests
from navegador_cdp import get_driver

SESSION_FILE = ".moodle_session.json"
SESSION_TTL_DAYS = 7


def _session_path() -> Path:
    """Ruta al archivo de sesión persistente."""
    return Path(SESSION_FILE).resolve()


def guardar_cookies_selenium() -> bool:
    """
    Extrae cookies del driver Selenium activo y las guarda en disco.

    Returns:
        True si se guardaron cookies válidas.
    """
    driver = get_driver()
    if not driver:
        print("[WARN] No hay driver Selenium activo")
        return False

    cookies = driver.get_cookies()
    if not cookies:
        print("[WARN] No se encontraron cookies en el navegador")
        return False

    session_data = {
        "cookies": cookies,
        "url_base": driver.current_url.split("/course/view.php")[0],
    }

    path = _session_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2)

    print(f"[OK] Sesión guardada en {path} ({len(cookies)} cookies)")
    return True


def cargar_session_requests() -> requests.Session | None:
    """
    Carga cookies guardadas en un requests.Session listo para usar.

    Returns:
        Session configurada o None si no hay sesión guardada/válida.
    """
    path = _session_path()
    if not path.exists():
        return None

    # Verificar TTL
    import time
    if time.time() - path.stat().st_mtime > SESSION_TTL_DAYS * 24 * 3600:
        print("[WARN] Sesión expirada (más de 7 días)")
        return None

    with open(path, encoding="utf-8") as f:
        session_data = json.load(f)

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.verify = False  # Moodle tiene certificado auto-firmado
    for c in session_data.get("cookies", []):
        session.cookies.set(
            name=c["name"],
            value=c["value"],
            domain=c.get("domain", ""),
            path=c.get("path", "/"),
        )

    # Establecer headers típicos de Moodle
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    })

    return session


def tiene_sesion_valida() -> bool:
    """Verifica si existe una sesión guardada reciente."""
    path = _session_path()
    if not path.exists():
        return False
    import time
    return time.time() - path.stat().st_mtime <= SESSION_TTL_DAYS * 24 * 3600


def eliminar_sesion() -> None:
    """Elimina el archivo de sesión."""
    path = _session_path()
    if path.exists():
        path.unlink()
        print("[OK] Sesión eliminada")
