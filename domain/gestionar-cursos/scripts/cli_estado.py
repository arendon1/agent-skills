#!/usr/bin/env python3
"""
CLI estado: /gestionar-cursos estado <CARPETA_CURSO>

Compara _cache/snapshot.json contra el estado actual en Moodle.
Detecta: actividades nuevas, fechas modificadas, actividades eliminadas.
Usa paralelismo por unidad para extraer fechas de quiz/assign/forum/lesson/workshop.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel

# Asegurar que scripts/ esté en path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from browser_api import (
    esta_usando_selenium,
    extraer_sidebar,
    get_current_url,
    get_navegador,
    set_profile_dir,
)
from cli_init import _url_key
from extractor_foro_evaluable import (
    cargar_cache_foros,
    es_evaluable,
    extraer_datos_foro,
)

console = Console()
BASE_URL = "https://aulavirtual.uniremington.edu.co"


def cargar_snapshot(ruta_curso: str) -> dict:
    """Carga _cache/snapshot.json o retorna vacío."""
    path = os.path.join(ruta_curso, "_cache", "snapshot.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"timestamp": "", "actividades": {}}


def guardar_snapshot(ruta_curso: str, snapshot: dict):
    """Guarda snapshot actualizado.

    Preserva campos extra que no controla `estado` (ej: `calificacion`,
    `calificaciones_capturadas` que escribe `cli_calificaciones.py`).
    Sin esta preservación, re-ejecutar `estado` borraría las notas
    recién capturadas.
    """
    cache_dir = os.path.join(ruta_curso, "_cache")
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "snapshot.json")

    # Preservar campos que no son de nuestra incumbencia
    snapshot_anterior = {}
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                snapshot_anterior = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    campos_preservados = (
        "calificaciones_capturadas",
        # `calificacion` vive dentro de cada actividad, lo manejamos abajo
    )
    for campo in campos_preservados:
        if campo in snapshot_anterior and campo not in snapshot:
            snapshot[campo] = snapshot_anterior[campo]

    # Preservar `calificacion` por actividad si no se está actualizando
    actividades_nuevas = snapshot.get("actividades", {})
    actividades_viejas = snapshot_anterior.get("actividades", {})
    for key, nueva in actividades_nuevas.items():
        vieja = actividades_viejas.get(key, {})
        if "calificacion" in vieja and "calificacion" not in nueva:
            nueva["calificacion"] = vieja["calificacion"]
        # No pisar si la nueva ya tiene `calificacion` (re-fetch)
        elif "calificacion" in vieja and "calificacion" in nueva:
            # Si la nueva no tiene `actualizado` (caso raro), preservar
            if not nueva["calificacion"].get("actualizado"):
                # Conservar campos extra que la nueva no haya poblado
                for k, v in vieja["calificacion"].items():
                    nueva["calificacion"].setdefault(k, v)

    snapshot["timestamp"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)


def extraer_sidebar_actual(url_curso: str) -> list[dict]:
    """Navega al curso y extrae sidebar actual."""
    navegador = get_navegador()
    navegador(url_curso)
    url_actual = get_current_url()
    if "login" in url_actual.lower():
        raise RuntimeError("Sesión expirada. Haz login en Moodle primero.")

    sidebar = extraer_sidebar()
    # Filtrar solo actividades con URL
    items = []
    seccion_actual = ""
    for item in sidebar:
        if item.get("tipo") == "seccion":
            seccion_actual = item.get("nombre", "")
        elif item.get("url"):
            items.append({
                "nombre": item.get("nombre", ""),
                "url": item["url"],
                "tipo": item.get("tipo", "unknown"),
                "seccion": seccion_actual,
            })
    return items


def extraer_url_curso(ruta_curso: str) -> str:
    """Extrae URL del curso desde AGENTS.md."""
    agents_path = os.path.join(ruta_curso, "AGENTS.md")
    if not os.path.isfile(agents_path):
        raise FileNotFoundError(f"No se encontró AGENTS.md en {ruta_curso}")
    with open(agents_path, encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'\*\*URL\*\*:\s*(https?://[^\s]+)', content)
    if m:
        return m.group(1).strip()
    m = re.search(r'(https?://aulavirtual[^\s]+)', content)
    if m:
        return m.group(1).strip()
    raise ValueError("No se encontró URL del curso en AGENTS.md")


def comparar_snapshots(snapshot_ant: dict, sidebar_actual: list[dict]) -> dict:
    """Compara sidebar actual contra snapshot anterior.

    Returns:
        {"nuevas": [...], "eliminadas": [...], "existentes": [...], "cambios_fecha": [...]}
    """
    act_anteriores = snapshot_ant.get("actividades", {})
    urls_anteriores = set(act_anteriores.keys())

    nuevas = []
    existentes = []
    urls_actuales = set()

    for item in sidebar_actual:
        key = _url_key(item["url"])
        urls_actuales.add(key)
        if key not in urls_anteriores:
            nuevas.append({**item, "key": key})
        else:
            existentes.append({**item, "key": key})

    eliminadas = []
    for key in urls_anteriores - urls_actuales:
        eliminadas.append({**act_anteriores[key], "key": key})

    return {
        "nuevas": nuevas,
        "eliminadas": eliminadas,
        "existentes": existentes,
    }


def extraer_fechas_paralelo(actividades_por_unidad: dict[str, list[dict]],
                            profile_dir: str) -> dict[str, dict]:
    """Lanza subprocesos por unidad para extraer fechas de quiz/assign.

    Cada subproceso recibe la lista de actividades de su unidad,
    visita cada quiz/assign, y devuelve {key: {fecha_apertura, fecha_cierre}}.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fechas = {}

    for unidad, acts in actividades_por_unidad.items():
        if not acts:
            continue
        quiz_assign = [a for a in acts if a["tipo"] in ("quiz", "assign", "forum", "lesson", "workshop")]
        if not quiz_assign:
            continue

        payload = json.dumps(quiz_assign, ensure_ascii=False)
        proceso_script = os.path.join(script_dir, "_extraer_fechas_unidad.py")

        console.print(f"  [dim]Unidad: {unidad} ({len(quiz_assign)} quiz/assign)[/dim]")
        try:
            p = subprocess.run(
                [sys.executable, proceso_script,
                 "--profile-dir", profile_dir],
                input=payload, capture_output=True, text=True,
                encoding="utf-8", timeout=120,
            )
            if p.returncode == 0 and p.stdout.strip():
                fechas_unidad = json.loads(p.stdout)
                fechas.update(fechas_unidad)
                console.print(f"    [green]✓ {len(fechas_unidad)} fechas extraídas[/green]")
            else:
                console.print(f"    [yellow]Error: {p.stderr[:200] if p.stderr else 'sin output'}[/yellow]")
        except Exception as e:
            console.print(f"    [yellow]Error subproceso: {e}[/yellow]")

    return fechas


def diff_fechas(snapshot_ant: dict, fechas_actuales: dict[str, dict]) -> list[dict]:
    """Compara fechas extraídas contra snapshot."""
    cambios = []
    act_anteriores = snapshot_ant.get("actividades", {})
    for key, fechas in fechas_actuales.items():
        ant = act_anteriores.get(key, {})
        apertura_ant = ant.get("fecha_apertura", "")
        cierre_ant = ant.get("fecha_cierre", "")
        apertura_nueva = fechas.get("fecha_apertura", "")
        cierre_nueva = fechas.get("fecha_cierre", "")

        if (apertura_nueva and apertura_nueva != apertura_ant) or \
           (cierre_nueva and cierre_nueva != cierre_ant):
            cambios.append({
                "key": key,
                "nombre": ant.get("nombre", fechas.get("nombre", "")),
                "tipo": ant.get("tipo", ""),
                "seccion": ant.get("seccion", ""),
                "fecha_apertura_ant": apertura_ant,
                "fecha_apertura_nueva": apertura_nueva,
                "fecha_cierre_ant": cierre_ant,
                "fecha_cierre_nueva": cierre_nueva,
            })
    return cambios


def revisar_hilos_foros_evaluables(
    sidebar_actual: list[dict], ruta_curso: str
) -> list[str]:
    """
    Para cada foro en una sección de unidad, lo visita, extrae su
    listado de hilos, y compara contra el cache local. Devuelve una
    lista de bloques markdown (uno por foro con cambios).
    """
    import re

    _RE_UNIDAD = re.compile(r"^Unidad\s+(\d+)", re.IGNORECASE)
    cache = cargar_cache_foros(ruta_curso)
    bloques: list[str] = []

    seccion_actual = ""
    for item in sidebar_actual:
        if item.get("tipo") == "seccion":
            seccion_actual = item.get("nombre", "")
            continue
        if item.get("tipo") != "forum":
            continue
        if not _RE_UNIDAD.match((seccion_actual or "").strip()):
            continue
        if not es_evaluable(item.get("nombre", ""))[0]:
            continue
        nombre_foro = item.get("nombre", "")
        try:
            datos = extraer_datos_foro(item["url"])
        except Exception as e:  # noqa: BLE001
            bloques.append(f"### ⚠ {nombre_foro}\n- Error al revisar: {e}")
            continue
        ids_cacheados = {k for k, v in cache.items() if v.get("url")}
        ids_actuales = {h["discuss_id"] for h in datos["hilos"]}
        nuevos = sorted(ids_actuales - ids_cacheados)
        removidos = sorted(ids_cacheados - ids_actuales)
        if not nuevos and not removidos:
            continue
        partes = [f"### {nombre_foro}"]
        if nuevos:
            partes.append(f"- **Hilos nuevos ({len(nuevos)}):** {', '.join(nuevos)}")
        if removidos:
            partes.append(f"- **Hilos removidos ({len(removidos)}):** {', '.join(removidos)}")
        bloques.append("\n".join(partes))

    return bloques


def generar_reporte(diff: dict, cambios_fecha: list[dict]) -> str:
    """Genera reporte markdown del diff."""
    nuevas = diff["nuevas"]
    eliminadas = diff["eliminadas"]

    if not nuevas and not eliminadas and not cambios_fecha:
        return "✅ Sin cambios detectados."

    partes = []
    if nuevas:
        partes.append(f"### 🆕 Actividades nuevas ({len(nuevas)})")
        for a in nuevas:
            partes.append(f"- **{a['nombre']}** ({a['tipo']}) — {a['seccion']}")

    if cambios_fecha:
        partes.append(f"### 📅 Fechas modificadas ({len(cambios_fecha)})")
        for c in cambios_fecha:
            detalle = f"- **{c['nombre']}** ({c['seccion']})"
            if c["fecha_cierre_ant"] != c["fecha_cierre_nueva"]:
                detalle += f"\n  - Cierre: {c['fecha_cierre_ant']} → **{c['fecha_cierre_nueva']}**"
            if c["fecha_apertura_ant"] != c["fecha_apertura_nueva"]:
                detalle += f"\n  - Apertura: {c['fecha_apertura_ant']} → **{c['fecha_apertura_nueva']}**"
            partes.append(detalle)

    if eliminadas:
        partes.append(f"### 🗑️ Actividades eliminadas/ocultas ({len(eliminadas)})")
        for a in eliminadas:
            partes.append(f"- ~~{a.get('nombre', a.get('key', ''))}~~ ({a.get('seccion', '')})")

    return "\n\n".join(partes)


def main():
    parser = argparse.ArgumentParser(
        description="Verificar estado de curso local vs Moodle"
    )
    parser.add_argument("carpeta", help="Ruta a la carpeta del curso")
    parser.add_argument(
        "--sync", action="store_true",
        help="Sincronizar automáticamente si hay cambios"
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="No abrir Chrome; asume CDP corriendo en localhost:9222"
    )
    parser.add_argument(
        "--profile-dir", "-p", default=None,
        help="Directorio para perfil persistente de Chrome"
    )
    args = parser.parse_args()

    ruta_curso = os.path.abspath(args.carpeta)
    if not os.path.isdir(ruta_curso):
        console.print(f"[bold red]ERROR:[/bold red] No existe: {ruta_curso}")
        sys.exit(1)

    console.print(Panel.fit(
        "[bold]GESTIONAR-CURSOS[/bold] :: ESTADO",
        style="bold cyan", border_style="cyan"
    ))

    # Configurar Chrome
    profile = args.profile_dir or os.path.join(os.getcwd(), ".browserdata")
    set_profile_dir(profile)

    if not esta_usando_selenium():
        console.print("[bold red]ERROR:[/bold red] No se detectó modo CDP/Selenium.")
        sys.exit(1)

    # Cargar snapshot anterior
    snapshot_ant = cargar_snapshot(ruta_curso)
    if not snapshot_ant.get("actividades"):
        console.print(Panel(
            "No se encontró snapshot (_cache/snapshot.json).\n"
            "Ejecuta primero: [code]uv run python cli_init.py <URL>[/code]",
            title="[bold yellow]Sin snapshot[/bold yellow]",
            border_style="yellow"
        ))
        sys.exit(0)

    ts_ant = snapshot_ant.get("timestamp", "desconocido")
    console.print(f"[dim]Última snapshot: {ts_ant}[/dim]")

    # Extraer URL del curso
    try:
        url_curso = extraer_url_curso(ruta_curso)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]ERROR:[/bold red] {e}")
        sys.exit(1)

    # Extraer sidebar actual
    console.print("\n[bold cyan][1/4][/bold cyan] Extrayendo barra lateral actual...")
    try:
        sidebar_actual = extraer_sidebar_actual(url_curso)
        console.print(f"    [green]{len(sidebar_actual)} actividades visibles[/green]")
    except RuntimeError as e:
        console.print(f"[bold red]ERROR:[/bold red] {e}")
        sys.exit(1)

    # Comparar URLs
    console.print("[bold cyan][2/4][/bold cyan] Comparando contra snapshot...")
    diff = comparar_snapshots(snapshot_ant, sidebar_actual)
    console.print(
        f"    Nuevas: {len(diff['nuevas'])} | "
        f"Eliminadas: {len(diff['eliminadas'])} | "
        f"Existentes: {len(diff['existentes'])}"
    )

    # Extraer fechas en paralelo por unidad
    console.print("[bold cyan][3/4][/bold cyan] Extrayendo fechas (paralelo por unidad)...")
    actividades_por_unidad = {}
    for item in sidebar_actual:
        seccion = item.get("seccion", "General")
        actividades_por_unidad.setdefault(seccion, []).append(item)

    fechas_actuales = extraer_fechas_paralelo(actividades_por_unidad, profile)

    # Diff de fechas
    cambios_fecha = diff_fechas(snapshot_ant, fechas_actuales)

    # Actualizar snapshot con fechas extraídas
    for item in sidebar_actual:
        key = _url_key(item["url"])
        fechas = fechas_actuales.get(key, {})
        if item["tipo"] in ("quiz", "assign", "forum", "lesson", "workshop") and fechas:
            item["fecha_apertura"] = fechas.get("fecha_apertura", "")
            item["fecha_cierre"] = fechas.get("fecha_cierre", "")

    nueva_snapshot = {
        "actividades": {
            _url_key(item["url"]): {
                "nombre": item["nombre"],
                "tipo": item["tipo"],
                "seccion": item["seccion"],
                "fecha_apertura": item.get("fecha_apertura", ""),
                "fecha_cierre": item.get("fecha_cierre", ""),
            }
            for item in sidebar_actual
        }
    }
    guardar_snapshot(ruta_curso, nueva_snapshot)

    # Reporte
    console.print("\n[bold cyan][4/4][/bold cyan] Resultado:")
    reporte = generar_reporte(diff, cambios_fecha)
    console.print(Panel(reporte, title="[bold]Diff[/bold]", border_style="green"))

    # Diff de hilos en foros evaluables
    console.print("\n[bold cyan][5/5][/bold cyan] Revisando hilos en foros evaluables...")
    reportes_foros = revisar_hilos_foros_evaluables(sidebar_actual, ruta_curso)
    if reportes_foros:
        bloque = "\n\n".join(reportes_foros)
        console.print(Panel(bloque, title="[bold]Foros[/bold]", border_style="magenta"))
    else:
        console.print("    [dim]Sin foros evaluables en unidades.[/dim]")

    if args.sync and (diff["nuevas"] or cambios_fecha):
        console.print("\n[bold yellow]Sincronización pendiente:[/bold yellow]")
        console.print(f"  uv run python cli_init.py {url_curso} --destino "
                      f"{os.path.dirname(ruta_curso)}")
    if args.sync and any("Hilos nuevos" in r for r in reportes_foros):
        console.print("\n[bold magenta]Hilos nuevos detectados.[/bold magenta]")
        console.print(f"  uv run python cli_foros.py {ruta_curso}")


if __name__ == "__main__":
    main()
