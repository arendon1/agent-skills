#!/usr/bin/env python3
"""
CLI foros: /gestionar-cursos foros <CARPETA_CURSO>

Extrae los foros evaluables (>0% en título) de un curso, captura
metadata + hilos principales de compañeros (sin replies), y los guarda
en `Unidad-X/Foros/<forum-slug>.md`. Usa cache por `discuss_id`.

Uso:
    uv run python cli_foros.py "C:/.../2026-2-B1/MATERIA"
    uv run python cli_foros.py "C:/.../2026-2-B1/MATERIA" --dry-run
"""

import argparse
import os
import re
import sys

# Asegurar que scripts/ esté en path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel

from browser_api import (
    esta_usando_selenium,
    extraer_sidebar,
    get_current_url,
    get_navegador,
    set_profile_dir,
)
from extractor_foro_evaluable import (
    MAX_HILOS,
    cargar_cache_foros,
    es_evaluable,
    extraer_datos_foro,
    extraer_primer_post_cached,
    guardar_cache_foros,
)

console = Console()

_RE_UNIDAD = re.compile(r"^Unidad\s+(\d+)", re.IGNORECASE)


def _slug_foro(titulo: str) -> str:
    """Convierte 'Foro 1: Seguridad en aplicaciones web (6%)' → 'Foro_1_Seguridad_en_aplicaciones_web_6'."""
    s = re.sub(r"\(\d+%\)", "", titulo or "")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s[:80] or "Foro"


def _leer_url_curso(ruta_curso: str) -> str:
    agents = os.path.join(ruta_curso, "AGENTS.md")
    if not os.path.isfile(agents):
        raise FileNotFoundError(f"No se encontró AGENTS.md en {ruta_curso}")
    with open(agents, encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"\*\*URL\*\*:\s*(https?://[^\s]+)", content)
    if m:
        return m.group(1).strip()
    m = re.search(r"(https?://aulavirtual[^\s]+)", content)
    if m:
        return m.group(1).strip()
    raise ValueError("No se encontró URL del curso en AGENTS.md")


def _seccion_es_unidad(seccion: str) -> tuple[bool, int]:
    """Devuelve (es_unidad, numero). 'Unidad 1' → (True, 1). 'General' → (False, 0)."""
    m = _RE_UNIDAD.match(seccion.strip())
    if not m:
        return False, 0
    return True, int(m.group(1))


def _carpeta_unidad_foro(ruta_curso: str, seccion: str) -> str:
    """Resuelve la ruta de la carpeta Unidad-X/Foros/ a partir del nombre de sección."""
    es_unidad, num = _seccion_es_unidad(seccion)
    if es_unidad:
        carpeta = os.path.join(ruta_curso, f"Unidad-{num}", "Foros")
    else:
        # Foro en sección 0/intro: va a "General/Foros" o similar.
        # Si no existe "General", crear carpeta con nombre saneado de la sección.
        carpeta = os.path.join(ruta_curso, "General", "Foros")
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def _renderizar_markdown(datos: dict, hilos_con_contenido: list[dict]) -> str:
    """Compone el markdown final de un foro evaluable."""
    titulo = datos["titulo"] or "Foro sin título"
    porcentaje = datos.get("porcentaje", 0)
    vencimiento = datos.get("vencimiento") or "[Sin vencimiento]"
    url = datos.get("url", "")
    indicaciones = datos.get("indicaciones") or "[Sin indicaciones]"
    actividad = datos.get("actividad") or "[Sin actividad especificada]"
    hilos = datos.get("hilos", [])

    total_visibles = len(hilos)
    extraidos = len(hilos_con_contenido)

    out = [
        f"# {titulo}",
        "",
        f"- **URL:** {url}",
        f"- **Vencimiento:** {vencimiento}",
        f"- **Calificación:** {porcentaje}%",
        f"- **Hilos extraídos:** {extraidos} (de {total_visibles} visibles, cap {MAX_HILOS})",
        "",
        "## Indicaciones",
        "",
        indicaciones,
        "",
        "## Actividad a realizar",
        "",
        actividad,
        "",
        "## Hilos principales de compañeros",
        "",
    ]

    for i, hilo in enumerate(hilos_con_contenido, 1):
        out.extend([
            f"### {i}. {hilo['titulo']} (ID: {hilo['discuss_id']})",
            "",
            f"- **Iniciado por:** {hilo['autor']} — {hilo['fecha']}",
            f"- **Última respuesta:** {hilo['ultimo_mensaje_autor']} — {hilo['ultimo_mensaje_fecha']}",
            f"- **Réplicas:** {hilo['replicas']}",
            f"- **URL:** {hilo['url']}",
            "",
            "#### Primer post",
            "",
            hilo.get("contenido") or "[Sin contenido extraído]",
            "",
            "---",
            "",
        ])

    return "\n".join(out)


def procesar_curso(ruta_curso: str, dry_run: bool = False) -> None:
    """
    Itera el sidebar del curso, identifica foros evaluables en
    unidades, extrae metadata + hilos, guarda markdown por foro.
    """
    ruta_curso = os.path.abspath(ruta_curso)
    if not os.path.isdir(ruta_curso):
        console.print(f"[bold red]ERROR:[/bold red] No existe: {ruta_curso}")
        sys.exit(1)

    console.print(Panel.fit(
        "[bold]GESTIONAR-CURSOS[/bold] :: FOROS EVALUABLES",
        style="bold cyan", border_style="cyan",
    ))

    # Configurar Chrome
    profile = os.path.join(os.getcwd(), ".browserdata")
    set_profile_dir(profile)
    if not esta_usando_selenium():
        console.print("[bold red]ERROR:[/bold red] No se detectó modo CDP/Selenium.")
        sys.exit(1)

    # URL del curso
    try:
        url_curso = _leer_url_curso(ruta_curso)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]ERROR:[/bold red] {e}")
        sys.exit(1)
    console.print(f"[dim]Curso:[/dim] {url_curso}")

    # Sidebar
    console.print("\n[bold cyan][1/4][/bold cyan] Extrayendo sidebar...")
    navegador = get_navegador()
    navegador(url_curso)
    if "login" in (get_current_url() or "").lower():
        console.print("[bold red]ERROR:[/bold red] Sesión expirada. Inicia sesión en Moodle.")
        sys.exit(1)

    sidebar = extraer_sidebar()
    foros_por_seccion: list[dict] = []
    seccion_actual = ""
    for item in sidebar:
        if item.get("tipo") == "seccion":
            seccion_actual = item.get("nombre", "")
        elif item.get("url") and item.get("tipo") == "forum":
            foros_por_seccion.append({
                "nombre": item.get("nombre", ""),
                "url": item["url"],
                "seccion": seccion_actual,
            })

    console.print(f"    [green]{len(foros_por_seccion)} foros en sidebar[/green]")

    # Filtrar por "Unidad X"
    en_unidades = [f for f in foros_por_seccion if _seccion_es_unidad(f["seccion"])[0]]
    if not en_unidades:
        console.print(Panel(
            "No se encontraron foros en secciones tipo 'Unidad X'.\n"
            "Los foros introductorios (Avisos, Consultas) NO se procesan aquí.\n"
            "Usa `init` para extraer los foros introductorios a COMUNICACION/.",
            title="[bold yellow]Sin foros de unidad[/bold yellow]",
            border_style="yellow",
        ))
        return

    console.print(f"    [cyan]{len(en_unidades)} foros en secciones de unidad[/cyan]")

    # Cargar cache
    cache = cargar_cache_foros(ruta_curso)

    # Procesar cada foro
    console.print("\n[bold cyan][2/4][/bold cyan] Extrayendo metadata de cada foro...")
    resultados: list[dict] = []
    omitidos = 0
    for f in en_unidades:
        evaluable, _ = es_evaluable(f["nombre"])
        if not evaluable:
            console.print(
                f"    [yellow]Omitido (no evaluable):[/yellow] {f['nombre']}"
            )
            omitidos += 1
            continue
        console.print(f"    [cyan]Procesando:[/cyan] {f['nombre']}  [dim]({f['seccion']})[/dim]")
        try:
            datos = extraer_datos_foro(f["url"])
        except Exception as e:  # noqa: BLE001
            console.print(f"      [red]Error:[/red] {e}")
            continue
        resultados.append({"seccion": f["seccion"], "datos": datos})

    console.print(f"    [green]{len(resultados)} foros evaluables, {omitidos} omitidos[/green]")

    if not resultados:
        console.print(Panel(
            "Ningún foro pasó el filtro de evaluable.\n"
            "Verifica que el título incluya `(X%)` con X>0.",
            title="[bold yellow]Sin foros evaluables[/bold yellow]",
            border_style="yellow",
        ))
        return

    # Extraer contenido del primer post de cada hilo (con cache)
    console.print("\n[bold cyan][3/4][/bold cyan] Extrayendo primeros posts (con cache)...")
    total_hilos = 0
    cache_hits = 0
    for r in resultados:
        hilos_contenido: list[dict] = []
        for hilo in r["datos"]["hilos"]:
            discuss_id = hilo["discuss_id"]
            if discuss_id in cache and cache[discuss_id].get("contenido"):
                cache_hits += 1
            contenido = extraer_primer_post_cached(
                discuss_id, hilo["url"], cache
            )
            hilo["contenido"] = contenido
            hilos_contenido.append(hilo)
        r["hilos_con_contenido"] = hilos_contenido
        total_hilos += len(hilos_contenido)
    console.print(
        f"    [green]{total_hilos} hilos procesados[/green] "
        f"[dim]({cache_hits} desde cache)[/dim]"
    )

    # Guardar archivos markdown
    console.print("\n[bold cyan][4/4][/bold cyan] Guardando archivos markdown...")
    if dry_run:
        console.print("    [yellow]DRY-RUN: nada se escribe[/yellow]")
    for r in resultados:
        carpeta = _carpeta_unidad_foro(ruta_curso, r["seccion"])
        slug = _slug_foro(r["datos"]["titulo"])
        ruta_md = os.path.join(carpeta, f"{slug}.md")
        md = _renderizar_markdown(r["datos"], r["hilos_con_contenido"])
        if dry_run:
            console.print(f"    [dim]DRY[/dim] {ruta_md}  ({len(md)} bytes)")
        else:
            with open(ruta_md, "w", encoding="utf-8") as f:
                f.write(md)
            console.print(f"    [green]OK[/green] {ruta_md}")

    if not dry_run:
        guardar_cache_foros(ruta_curso, cache)
        console.print(f"\n[dim]Cache actualizado: _cache/foros_cache.json ({len(cache)} hilos)[/dim]")

    console.print(Panel.fit(
        f"[bold green]Listo:[/bold green] {len(resultados)} foros evaluables procesados, "
        f"{total_hilos} hilos extraídos.",
        style="green",
    ))


def main():
    parser = argparse.ArgumentParser(
        description="Extraer foros evaluables y sus hilos principales de compañeros"
    )
    parser.add_argument("carpeta", help="Ruta a la carpeta del curso (la que contiene AGENTS.md)")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="No escribir archivos ni cache; solo mostrar lo que haría",
    )
    args = parser.parse_args()
    procesar_curso(args.carpeta, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
