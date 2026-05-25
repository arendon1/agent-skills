"""
Browser API abstraction layer.

Expone funciones que los scripts del skill usan para navegar.
En entorno de agente (VS Code / OpenCode IDE) usa las tools inyectadas.
En terminal fallback a Chrome DevTools Protocol via Selenium.
"""

import sys

# ---------------------------------------------------------------------------
# Detección de modo agente
# ---------------------------------------------------------------------------

def _agent_has_tool():
    """Verifica si el framework de agente inyectó tools de navegación."""
    import builtins
    return (
        getattr(builtins, 'browser_tool', None) is not None
        or getattr(builtins, 'open_browser', None) is not None
    )


# ---------------------------------------------------------------------------
# Carga lazy de fallback CDP
# ---------------------------------------------------------------------------

_cdp_funcs = None


def _load_cdp():
    global _cdp_funcs
    if _cdp_funcs is not None:
        return _cdp_funcs

    try:
        from navegador_cdp import (
            navegar,
            obtener_url_actual,
            obtener_contenido,
            click,
            esperar_carga,
            encontrar_menus_cerrados,
            extraer_sidebar,
            extraer_texto_descripcion,
            extraer_instrucciones,
            extraer_links_materiales,
            extraer_criterios,
            extraer_nombre_unidad,
            obtener_cookies,
            hacer_get,
            extraer_filas_tabla,
            get_driver,
        )
        _cdp_funcs = {
            'navegar': navegar,
            'obtener_url_actual': obtener_url_actual,
            'obtener_contenido': obtener_contenido,
            'click': click,
            'esperar_carga': esperar_carga,
            'encontrar_menus_cerrados': encontrar_menus_cerrados,
            'extraer_sidebar': extraer_sidebar,
            'extraer_texto_descripcion': extraer_texto_descripcion,
            'extraer_instrucciones': extraer_instrucciones,
            'extraer_links_materiales': extraer_links_materiales,
            'extraer_criterios': extraer_criterios,
            'extraer_nombre_unidad': extraer_nombre_unidad,
            'obtener_cookies_browser': obtener_cookies,
            'hacer_get': hacer_get,
            'extraer_filas_tabla': extraer_filas_tabla,
            'get_driver': get_driver,
        }
        return _cdp_funcs
    except ImportError as e:
        raise RuntimeError(
            "No hay tool de navegación disponible y no se pudo cargar "
            "el fallback CDP/Selenium. Asegúrate de tener instalado:\n"
            "  pip install selenium beautifulsoup4 lxml requests\n"
            f"Error original: {e}"
        ) from e


def _get_func(name: str):
    """Obtiene función de agente o fallback CDP."""
    if _agent_has_tool():
        import builtins
        val = getattr(builtins, name, None)
        if val is None:
            raise RuntimeError(
                f"Función '{name}' no encontrada en el entorno de agente."
            )
        return val
    return _load_cdp()[name]


# ---------------------------------------------------------------------------
# API pública (mismos nombres que los scripts esperan)
# ---------------------------------------------------------------------------

def get_navegador():
    """Retorna callable que navega a URL."""
    if _agent_has_tool():
        import builtins
        return getattr(builtins, 'browser_tool', None) or getattr(builtins, 'open_browser')
    return _load_cdp()['navegar']


def get_current_url():
    return _get_func('obtener_url_actual')()


def get_page_content():
    return _get_func('obtener_contenido')()


def click(element):
    return _get_func('click')(element)


def esperar_carga():
    return _get_func('esperar_carga')()


def encontrar_menus_cerrados():
    return _get_func('encontrar_menus_cerrados')()


def extraer_sidebar():
    return _get_func('extraer_sidebar')()


def extraer_texto_descripcion():
    return _get_func('extraer_texto_descripcion')()


def extraer_instrucciones():
    return _get_func('extraer_instrucciones')()


def extraer_links_materiales():
    return _get_func('extraer_links_materiales')()


def extraer_criterios():
    return _get_func('extraer_criterios')()


def extraer_nombre_unidad():
    return _get_func('extraer_nombre_unidad')()


def obtener_cookies_browser():
    return _get_func('obtener_cookies_browser')()


def hacer_get(url, headers=None):
    return _get_func('hacer_get')(url, headers)


def extraer_filas_tabla(html_content, header_text):
    return _get_func('extraer_filas_tabla')(html_content, header_text)


def esta_usando_selenium():
    """True si estamos en modo terminal con CDP/Selenium."""
    if _agent_has_tool():
        return False
    _load_cdp()
    return True


def get_driver():
    """Expone el driver Selenium directamente (solo modo CDP)."""
    if _agent_has_tool():
        raise RuntimeError("get_driver solo disponible en modo CDP/terminal")
    return _load_cdp()['get_driver']()
