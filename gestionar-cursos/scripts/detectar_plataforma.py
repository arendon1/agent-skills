"""
Detecta qué tool de navegación está disponible en el entorno.
Retorna: 'browser_tool' | 'open_browser' | 'selenium' | 'error'
"""

from browser_api import esta_usando_selenium


def detectar_navegacion():
    """
    Verifica cuál tool de browser está disponible.

    Orden de prioridad:
    1. browser_tool (VS Code / Antigravity - navegación headless)
    2. open_browser (OpenCode / fallback - ventana externa)
    3. selenium (Terminal / CLI - Chrome DevTools Protocol)
    4. Error si ninguna disponible
    """
    import builtins
    if getattr(builtins, 'browser_tool', None) is not None:
        return "browser_tool"

    if getattr(builtins, 'open_browser', None) is not None:
        return "open_browser"

    if esta_usando_selenium():
        return "selenium"

    return "error"


def get_navegador():
    """Retorna la función de navegación apropiada según plataforma."""
    from browser_api import get_navegador as _get_nav
    return _get_nav()
