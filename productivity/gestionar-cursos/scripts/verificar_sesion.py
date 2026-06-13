"""
Verifica el estado de autenticación en Moodle Uniremington.
"""

from browser_api import get_current_url, get_navegador, get_page_content

BASE_URL = "https://aulavirtual.uniremington.edu.co"


def verificar_pagina_actual():
    """
    Verifica si la PÁGINA ACTUAL (sin navegar) está autenticada.

    Returns:
        True si el contenido actual muestra sesión activa.
        False si parece no autenticado.
    """
    url_actual = get_current_url()

    if "login/index.php" in url_actual:
        return False

    page_content = get_page_content()

    if "Usted no se ha identificado" in page_content:
        return False

    return "Andres Felipe Rendon Hernandez" in page_content or "Área personal" in page_content


def verificar_sesion_moodle():
    """
    Navega a área personal Y verifica si está autenticado.

    Returns:
        True si autenticado, False si no.
    """
    navegador = get_navegador()
    navegador(BASE_URL + "/my/")
    return verificar_pagina_actual()


def requerir_sesion():
    """
    Verifica sesión y lanza error claro si no está autenticado.
    """
    if not verificar_sesion_moodle():
        raise RuntimeError(
            "Sesión no autenticada en Moodle. "
            "Por favor haz login manualmente en el navegador y avísame cuando estés listo."
        )
