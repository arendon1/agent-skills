"""
Verifica el estado de autenticación en Moodle Uniremington.
"""

from browser_api import get_navegador, get_current_url, get_page_content

BASE_URL = "https://aulavirtual.uniremington.edu.co"


def verificar_sesion_moodle():
    """
    Navega a la página de área personal y verifica si está autenticado.

    Returns:
        True si autenticado, False si no.

    Raises:
        RuntimeError si no se puede completar la verificación.
    """
    navegador = get_navegador()

    # Navegar a área personal
    navegador(BASE_URL + "/my/")

    # Obtener URL actual después de navegación
    url_actual = get_current_url()

    # Verificar indicadores de no autenticado
    if "login/index.php" in url_actual:
        return False

    # Verificar indicadores de autenticado
    page_content = get_page_content()

    if "Usted no se ha identificado" in page_content:
        return False

    if "Andres Felipe Rendon Hernandez" in page_content or "Área personal" in page_content:
        return True

    # Si no podemos determinar, asumir no autenticado
    return False


def requerir_sesion():
    """
    Verifica sesión y lanza error claro si no está autenticado.
    """
    if not verificar_sesion_moodle():
        raise RuntimeError(
            "Sesión no autenticada en Moodle. "
            "Por favor haz login manualmente en el navegador y avísame cuando estés listo."
        )