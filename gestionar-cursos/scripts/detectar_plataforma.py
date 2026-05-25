"""
Detecta qué tool de navegación está disponible en el entorno.
Retorna: 'browser_tool' | 'open_browser' | 'error'
"""

def detectar_navegacion():
    """
    Verifica cuál tool de browser está disponible.
    
    Orden de prioridad:
    1. browser_tool (VS Code / Antigravity - navegación headless)
    2. open_browser (OpenCode / fallback - ventana externa)
    3. Error si ninguna disponible
    """
    try:
        # Intentar browser_tool primero
        browser_tool()
        return "browser_tool"
    except NameError:
        pass  # browser_tool no existe
    
    try:
        # Fallback a open_browser genérico
        open_browser()
        return "open_browser"
    except NameError:
        pass  # open_browser no existe
    
    return "error"


def get_navegador():
    """Retorna la función de navegación apropiada según plataforma."""
    plataforma = detectar_navegacion()
    
    if plataforma == "error":
        raise RuntimeError(
            "No hay tool de navegación disponible. "
            "Instala un plugin de navegador o usa OpenCode con open_browser."
        )
    
    if plataforma == "browser_tool":
        return browser_tool  # Función de navegación headless
    else:
        return open_browser  # Abre ventana del sistema