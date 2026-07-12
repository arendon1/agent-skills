"""
Wrapper para procesar UN foro evaluable durante init/estado de una
unidad. Usado por `cli_init.py` (en el loop por actividad) y por
`cli_estado.py` (al detectar foros nuevos).

No itera el sidebar — recibe una sola actividad de tipo `forum` y la
procesa in-place.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

# Asegurar que scripts/ esté en path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractor_foro_evaluable import (
    cargar_cache_foros,
    es_evaluable,
    extraer_datos_foro,
    extraer_primer_post_cached,
    guardar_cache_foros,
)


_RE_UNIDAD = re.compile(r"^Unidad\s+(\d+)", re.IGNORECASE)


def _slug_foro(titulo: str) -> str:
    s = re.sub(r"\(\d+%\)", "", titulo or "")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s[:80] or "Foro"


def _carpeta_destino(ruta_curso: str, seccion: str) -> str:
    m = _RE_UNIDAD.match((seccion or "").strip())
    if m:
        carpeta = os.path.join(ruta_curso, f"Unidad-{m.group(1)}", "Foros")
    else:
        carpeta = os.path.join(ruta_curso, "General", "Foros")
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def _renderizar(datos: dict, hilos: list[dict]) -> str:
    out = [
        f"# {datos['titulo'] or 'Foro sin título'}",
        "",
        f"- **URL:** {datos.get('url', '')}",
        f"- **Vencimiento:** {datos.get('vencimiento') or '[Sin vencimiento]'}",
        f"- **Calificación:** {datos.get('porcentaje', 0)}%",
        f"- **Hilos extraídos:** {len(hilos)}",
        "",
        "## Indicaciones",
        "",
        datos.get("indicaciones") or "[Sin indicaciones]",
        "",
        "## Actividad a realizar",
        "",
        datos.get("actividad") or "[Sin actividad especificada]",
        "",
        "## Hilos principales de compañeros",
        "",
    ]
    for i, h in enumerate(hilos, 1):
        out.extend([
            f"### {i}. {h['titulo']} (ID: {h['discuss_id']})",
            "",
            f"- **Iniciado por:** {h['autor']} — {h['fecha']}",
            f"- **Última respuesta:** {h['ultimo_mensaje_autor']} — {h['ultimo_mensaje_fecha']}",
            f"- **Réplicas:** {h['replicas']}",
            f"- **URL:** {h['url']}",
            "",
            "#### Primer post",
            "",
            h.get("contenido") or "[Sin contenido extraído]",
            "",
            "---",
            "",
        ])
    return "\n".join(out)


def procesar_foro_en_unidad(act: dict[str, Any], ruta_curso: str, console) -> str:
    """
    Procesa un foro evaluable de una unidad durante init.

    Args:
        act: dict con {nombre, url, seccion, tipo:"forum"}.
        ruta_curso: ruta raíz del curso.
        console: rich.Console para output.

    Returns:
        Ruta del archivo markdown generado (o "" si se omitió).
    """
    nombre = act.get("nombre", "")
    evaluable, pct = es_evaluable(nombre)
    if not evaluable:
        console.print(f"      [yellow]No evaluable:[/yellow] {nombre}")
        return ""

    console.print(f"      [cyan]Foro evaluable ({pct}%):[/cyan] {nombre}")

    # 1. Metadata del foro
    datos = extraer_datos_foro(act["url"])

    # 2. Cache
    cache = cargar_cache_foros(ruta_curso)

    # 3. Primer post de cada hilo (cap implícito en extractor)
    hilos_con_contenido: list[dict] = []
    for hilo in datos["hilos"]:
        did = hilo["discuss_id"]
        contenido = extraer_primer_post_cached(did, hilo["url"], cache)
        hilo["contenido"] = contenido
        hilos_con_contenido.append(hilo)

    # 4. Guardar markdown
    carpeta = _carpeta_destino(ruta_curso, act.get("seccion", ""))
    slug = _slug_foro(datos["titulo"] or nombre)
    ruta_md = os.path.join(carpeta, f"{slug}.md")
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write(_renderizar(datos, hilos_con_contenido))

    # 5. Persistir cache
    guardar_cache_foros(ruta_curso, cache)

    console.print(f"        [green]OK[/green] {ruta_md}  [dim]({len(hilos_con_contenido)} hilos)[/dim]")
    return ruta_md
