"""
Crea archivos HTML proxy para contenido H5P de Moodle.
Permite visualización offline de interactivos.
"""

import os
import re

TEMPLATE_H5P = """<!DOCTYPE html>
<html>
<head>
    <title>{titulo}</title>
    <style>
        body {{
            margin: 0;
            display: flex;
            justify-content: center;
            background: #000;
            overflow: hidden;
            height: 100vh;
        }}
    </style>
</head>
<body>
    <iframe src="{embed_url}"
            width="100%"
            height="100%"
            style="border:0;"
            allowfullscreen="allowfullscreen"></iframe>
    <script src="https://aulavirtual.uniremington.edu.co/mod/hvp/library/js/h5p-resizer.js" charset="UTF-8"></script>
</body>
</html>"""

def extraer_h5p_id(url_h5p: str) -> str | None:
    """Extrae el ID del contenido H5P desde la URL."""
    # URL típica: https://aulavirtual.uniremington.edu.co/mod/hvp/view.php?id=12345
    match = re.search(r'[?&]id=(\d+)', url_h5p)
    if match:
        return match.group(1)
    return None


def crear_proxy_h5p(url_h5p: str, nombre: str, ruta_destino: str) -> bool:
    """
    Crea archivo HTML proxy para contenido H5P.

    Args:
        url_h5p: URL de la actividad H5P en Moodle
        nombre: Nombre para el archivo HTML (sin extensión)
        ruta_destino: Ruta donde guardar el proxy

    Returns:
        True si creado exitosamente
    """
    h5p_id = extraer_h5p_id(url_h5p)

    if not h5p_id:
        print(f"No se pudo extraer ID de H5P de: {url_h5p}")
        return False

    embed_url = f"https://aulavirtual.uniremington.edu.co/mod/hvp/embed.php?id={h5p_id}"

    html_content = TEMPLATE_H5P.format(
        titulo=nombre,
        embed_url=embed_url
    )

    # Asegurar extensión .html
    if not ruta_destino.endswith('.html'):
        ruta_destino += '.html'

    try:
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)

        with open(ruta_destino, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return True

    except Exception as e:
        print(f"Error creando proxy H5P: {e}")
        return False


def marcar_como_interactivo_en_sitemap(ruta_sitemap: str, nombre_proxy: str):
    """
    Actualiza sitemap.md para marcar el H5P como [Interactivo].
    """
    with open(ruta_sitemap, encoding='utf-8') as f:
        contenido = f.read()

    # Agregar etiqueta [Interactivo] si no existe
    if "[Interactivo]" not in contenido:
        contenido = contenido.replace(
            nombre_proxy,
            f"[Interactivo] {nombre_proxy}"
        )

    with open(ruta_sitemap, 'w', encoding='utf-8') as f:
        f.write(contenido)
