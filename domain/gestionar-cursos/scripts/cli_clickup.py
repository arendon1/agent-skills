#!/usr/bin/env python3
"""
CLI: /gestionar-cursos clickup-sync <PERIODO_DIR>

Modo PLAN-LOCAL (a partir de 2026-07-21, fix-gestionar-cursos-pipeline):

Este script SOLO produce un artefacto declarativo (sync_plan.json) que
describe la diferencia entre el estado local (Moodle snapshot + clickup.json)
y lo que deberia existir en ClickUp. NO toca la API de ClickUp.

La aplicacion de sync_plan.json la hace el agente con la skill
`use-clickup` (ver references/sync-flow.md para el playbook ejecutable).

Restricciones arquitectonicas (constraints C1, C4 del PRD):
- Cero imports de `use-clickup`. Cero llamadas HTTP. Solo filesystem + JSON.
- Direccion de flujo: Moodle -> Local -> ClickUp, unidireccional.
- to_archive NUNCA to_delete.

Uso:
    uv run python cli_clickup.py <PERIODO_DIR>
    uv run python cli_clickup.py <PERIODO_DIR> --dry-run
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

CLICKUP_SPACE_ID = "901311224662"
CLICKUP_SPACE_NAME = "Universidad"

# Schema version del sync_plan.json. Cualquier cambio incompatible
# requiere bumpear y migrar los planes legacy. Ver V7 del PRD.
SCHEMA_VERSION = 1

TOOLS_REQUIRED = [
    "use-clickup:create_task",
    "use-clickup:update_task",
    "use-clickup:post_comment",
]

SUPPORT_KEYWORDS = {
    "grupal": ["grupal", "grupo", "equipo", "colaborativo"],
    "entregable": ["entregable", "subir", "archivo", "enlace", "entregar"],
    "lectura": ["lectura", "leer"],
    "repaso": ["repaso", "estudiar", "preparar"],
    "documento": ["documento", "informe", "ensayo", "redact"],
    "investigar": ["investigar", "buscar", "fuentes"],
    "practica": ["practica", "ejercicio", "codigo", "laboratorio"],
    "exposicion": ["exposicion", "presentacion", "exponer", "sustent"],
    "participacion": ["participacion", "intervenir"],
}


# ---------------------------------------------------------------------------
# Tag / priority resolution
# ---------------------------------------------------------------------------

def _clasificar_actividad(nombre: str, valor_str: str) -> tuple[list[str], str]:
    """Returns (tags, prioridad) for an activity based on its name and weight."""
    tags = []
    prioridad = "normal"
    nombre_lower = nombre.lower()

    valor_num = 0.0
    if valor_str:
        try:
            valor_num = float(re.sub(r"[^\d.]", "", valor_str))
        except (ValueError, TypeError):
            pass

    # --- Tipo de actividad (mutually exclusive for priority) ---
    if valor_num >= 15 or "parcial" in nombre_lower:
        tags.append("parcial")
        prioridad = "urgente"
    elif any(kw in nombre_lower for kw in ["cuestionario", "prueba", "quiz", "examen", "leccion"]):
        tags.append("quiz")
        prioridad = "normal"
    elif "foro" in nombre_lower:
        tags.append("foro")
        tags.append("participacion")
        prioridad = "normal"
    else:
        tags.append("actividad")
        prioridad = "alta"

    # --- Evaluable / no evaluable ---
    if valor_num > 0 or any(kw in nombre_lower for kw in ["calificable", "evaluable"]):
        tags.append("evaluable")
    elif "no calificable" in nombre_lower or "no evaluable" in nombre_lower:
        tags.append("no-evaluable")
    elif "evaluable" not in tags and "no-evaluable" not in tags:
        tags.append("evaluable" if valor_num > 0 else "no-evaluable")

    # --- Soporte ---
    for tag, keywords in SUPPORT_KEYWORDS.items():
        if any(kw in nombre_lower for kw in keywords):
            if tag not in tags:
                tags.append(tag)

    return tags, prioridad


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_key(nombre: str) -> str:
    """Generate stable key for a task from its name."""
    return re.sub(r"[^a-z0-9_]", "_", nombre.lower().strip())[:60]


def _normalizar_nombre(nombre: str) -> str:
    """Quita sufijos '(X%)' / '(N/A)' del nombre para matching snapshot<->PGA."""
    return re.sub(r"\s*\([^)]*%[^)]*\)\s*$", "", nombre).strip()


def _parsear_pga_md(pga_path: str) -> list[dict]:
    """Parse PGA.md table into list of activity dicts."""
    if not os.path.isfile(pga_path):
        return []
    with open(pga_path, encoding="utf-8") as f:
        content = f.read()

    actividades = []
    in_table = False
    for line in content.split("\n"):
        if line.startswith("| Semana |") or line.startswith("| Semana  |"):
            in_table = True
            continue
        if line.startswith("|--"):
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 6:
                fecha_fin_raw = parts[5]
                fecha_inicio_iso = ""
                fecha_fin_iso = ""
                m = re.search(r"\((\d{4}-\d{2}-\d{2})\)", fecha_fin_raw)
                if m:
                    fecha_fin_iso = m.group(1)
                m = re.search(r"\((\d{4}-\d{2}-\d{2})\)", parts[4])
                if m:
                    fecha_inicio_iso = m.group(1)

                actividades.append({
                    "semana": parts[0],
                    "unidad": parts[1],
                    "actividad": parts[2],
                    "valor": parts[3],
                    "fecha_inicio": fecha_inicio_iso,
                    "fecha_fin": fecha_fin_iso,
                })
    return actividades


def _parsear_snapshot(ruta_curso: str) -> dict[str, dict[str, str]]:
    """Lee _cache/snapshot.json y devuelve {nombre_normalizado: {fecha_apertura, fecha_cierre, ...}}."""
    path = os.path.join(ruta_curso, "_cache", "snapshot.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    fechas: dict[str, dict] = {}
    for _key, act in snap.get("actividades", {}).items():
        nombre = act.get("nombre", "")
        if not nombre:
            continue
        norm = _normalizar_nombre(nombre)
        fa = act.get("fecha_apertura", "")
        fc = act.get("fecha_cierre", "")
        if fa or fc:
            fechas[norm] = {"fecha_apertura": fa, "fecha_cierre": fc}
    return fechas


def _parsear_calificaciones(ruta_curso: str) -> dict[str, dict]:
    """Lee _cache/calificaciones_<courseid>.json si existe.

    Devuelve {nombre_normalizado: {nota, estado, rango, porcentaje,
    aporte_curso, ponderacion_categoria, feedback}}.
    """
    cache_dir = os.path.join(ruta_curso, "_cache")
    if not os.path.isdir(cache_dir):
        return {}
    out: dict[str, dict] = {}
    for fname in os.listdir(cache_dir):
        if not fname.startswith("calificaciones_") or not fname.endswith(".json"):
            continue
        with open(os.path.join(cache_dir, fname), encoding="utf-8") as f:
            items = json.load(f)
        for it in items:
            nombre = it.get("nombre", "")
            if not nombre:
                continue
            norm = _normalizar_nombre(nombre)
            out[norm] = {
                "nota": it.get("calificacion") or None,
                "estado": it.get("estado", "Pendiente"),
                "rango": it.get("rango", ""),
                "porcentaje": it.get("porcentaje", ""),
                "aporte_curso": it.get("aporte_curso", ""),
                "ponderacion_categoria": it.get("ponderacion_pct", ""),
                "feedback": it.get("feedback", ""),
            }
    return out


def _resolver_periodo_dir(periodo_dir: str) -> tuple[str, str, str]:
    """Extract periodo and bloque from path like .../2026-2-B1."""
    dir_name = os.path.basename(os.path.abspath(periodo_dir))
    match = re.match(r"(\d{4}-\d)(?:-(B\d+))?", dir_name)
    if not match:
        return dir_name, dir_name, ""
    periodo = match.group(1)
    bloque = match.group(2) or ""
    return periodo, bloque, dir_name


def _encontrar_ruta_curso(periodo_dir: str, course_key: str) -> Optional[str]:
    """Find course directory inside periodo_dir (by Moodle ID or CODIGO)."""
    moodle_id_match = re.search(r"CURSO_(\d+)", course_key)
    moodle_id = moodle_id_match.group(1) if moodle_id_match else None
    codigo_match = re.search(r"CODIGO_?(\S+)", course_key)
    codigo = codigo_match.group(1) if codigo_match else None

    for entry in os.scandir(periodo_dir):
        if not entry.is_dir():
            continue
        agents_path = os.path.join(entry.path, "AGENTS.md")
        if not os.path.isfile(agents_path):
            continue
        with open(agents_path, encoding="utf-8") as f:
            content = f.read()

        if moodle_id:
            url_m = re.search(r"id=(\d+)", content)
            if url_m and url_m.group(1) == moodle_id:
                return entry.path
        if codigo:
            code_m = re.search(r"\*\*CODIGO\*\*:\s*(\S+)", content)
            if code_m and (course_key.endswith(code_m.group(1)) or course_key == code_m.group(1)):
                return entry.path
        else:
            code_m = re.search(r"\*\*CODIGO\*\*:\s*(\S+)", content)
            if code_m and code_m.group(1) in course_key:
                return entry.path
    return None


# ---------------------------------------------------------------------------
# Plan building
# ---------------------------------------------------------------------------

def _due_date_ms(fecha_iso: str) -> Optional[int]:
    """Convierte fecha ISO 'YYYY-MM-DD' a epoch ms (UTC midnight). None si vacio."""
    if not fecha_iso:
        return None
    try:
        dt = datetime.strptime(fecha_iso[:10], "%Y-%m-%d")
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def _ms_or_none(value) -> Optional[int]:
    """Coercion helper: si el valor es None o invalido, retorna None."""
    if value is None:
        return None
    return int(value) if value else None


def _build_create_entry(
    act: dict, list_id: str, fecha_inicio: str, fecha_fin: str, fecha_fuente: Optional[str]
) -> dict:
    """Construye entrada to_create para sync_plan.json."""
    nombre = act["actividad"]
    tags, prioridad = _clasificar_actividad(nombre, act["valor"])
    return {
        "task_id": None,
        "list_id": list_id,
        "name": nombre,
        "tags": tags,
        "priority": prioridad,
        "due_date_ms": _due_date_ms(fecha_fin),
        "start_date_ms": _due_date_ms(fecha_inicio),
        "due_date_source": fecha_fuente,
    }


def _needs_update_by_calificacion(act_calif: dict) -> bool:
    """¿La actividad calificada amerita to_update? (status + comment)."""
    return act_calif is not None and act_calif.get("nota")


def _build_update_entry(
    existing_task: dict,
    act_calif: dict,
    list_id: str,
) -> dict:
    """Construye entrada to_update con diff conservador (solo campos no-null).

    status SIEMPRE va a 'calificado' por nombre cuando hay nota. NUNCA
    enviamos status_id (L10, V5 del PRD).
    """
    task_id = existing_task.get("id", "")
    nombre = existing_task.get("name", "")
    return {
        "task_id": task_id,
        "list_id": list_id,
        "diff": {
            "status": {"from": "pendiente", "to": "calificado"},
            "name": None,
            "due_date_ms": None,
        },
        "comment": {
            "text": _render_calificacion_comment(act_calif, nombre),
            "tag": "[calificaciones-auto]",
        } if act_calif and act_calif.get("nota") else None,
    }


def _render_calificacion_comment(act_calif: dict, nombre: str) -> str:
    """Renderiza el comentario canonico con tag [calificaciones-auto]."""
    return (
        f"[calificaciones-auto] Calificacion sincronizada desde Moodle\n\n"
        f"- **Actividad:** {nombre}\n"
        f"- **Nota:** {act_calif.get('nota', '?')} / {act_calif.get('rango', '?')} "
        f"({act_calif.get('porcentaje', '?')})\n"
        f"- **Estado:** {act_calif.get('estado', 'Pendiente')}\n"
        f"- **Aporte al curso:** {act_calif.get('aporte_curso', '0,00 %')}\n"
        f"- **Capturado:** {datetime.now().isoformat(timespec='seconds')}"
    )


def _build_plan(
    clickup_data: dict,
    courses_dir: str,
    periodo: str,
    bloque: str,
) -> dict:
    """Calcula el delta entre clickup.json + snapshot.json/calificaciones.json
    locales y produce el sync_plan.json declarativo.

    Constraints:
    - Cero HTTP. Solo filesystem + JSON.
    - Si folder.id es null -> unresolved (no auto-resoluble).
    - Si list_id es null -> unresolved (el curso no esta inicializado).
    - to_update solo si hay calificacion.nota (idempotente con [calificaciones-auto]
      se valida en la pre-check del agente, no aqui).
    """
    folder_id = (clickup_data.get("folder") or {}).get("id")
    folder_name = f"{periodo}-{bloque}" if bloque else periodo

    plan = {
        "_meta": {
            "periodo": periodo,
            "bloque": bloque,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source": "moodle",
            "schema_version": SCHEMA_VERSION,
            "space": {"id": CLICKUP_SPACE_ID, "name": CLICKUP_SPACE_NAME},
            "folder": {"id": folder_id, "name": folder_name},
            "orchestration_hint": {
                "order": ["to_create", "to_update", "to_archive"],
                "tools_required": TOOLS_REQUIRED,
                "pause_for_human": [
                    "unresolved con razon no determinista (ver references/sync-flow.md §B)",
                ],
            },
            "idempotency_keys": {
                "to_create": "list_id + name",
                "to_update": "task_id + last_comment_startswith([calificaciones-auto])",
                "to_archive": "task_id + status==cancelled",
            },
        },
        "to_create": [],
        "to_update": [],
        "to_archive": [],
        "unresolved": [],
    }

    if not folder_id:
        plan["unresolved"].append({
            "item": "folder",
            "reason": "clickup.folder.id es null. Crear folder manualmente en ClickUp.",
        })
        # Sin folder no podemos resolver listas. Devolvemos el plan incompleto
        # y dejamos que el agente reporte al humano.
        return plan

    courses = clickup_data.get("courses", {})

    for course_key, course_info in courses.items():
        list_id = course_info.get("list_id")
        if not list_id:
            plan["unresolved"].append({
                "item": course_key,
                "reason": "clickup.list_id es null. Inicializar el curso (cli_init) o setear list_id manualmente.",
            })
            continue

        ruta_curso = _encontrar_ruta_curso(courses_dir, course_key)
        if not ruta_curso:
            plan["unresolved"].append({
                "item": course_key,
                "reason": "Carpeta de curso no encontrada en el periodo.",
            })
            continue

        pga_path = os.path.join(ruta_curso, "PGA.md")
        actividades = _parsear_pga_md(pga_path)
        snapshot_fechas = _parsear_snapshot(ruta_curso)
        calificaciones = _parsear_calificaciones(ruta_curso)
        existing_tasks: dict[str, dict] = {}
        for k, v in (course_info.get("tasks") or {}).items():
            existing_tasks[_task_key(k)] = v

        for act in actividades:
            nombre_act = act["actividad"]
            task_key = _task_key(nombre_act)
            norm = _normalizar_nombre(nombre_act)
            snap = snapshot_fechas.get(norm, {})

            # Resolver fecha con su fuente. Si snapshot tiene la fecha, esa es
            # la verdad (constraint C5). Si no, cae al PGA. La fuente debe
            # propagarse al sync_plan para que el agente sepa en que confiar.
            snap_fa = snap.get("fecha_apertura", "")
            snap_fc = snap.get("fecha_cierre", "")
            pga_fi = act.get("fecha_inicio", "")
            pga_ff = act.get("fecha_fin", "")

            if snap_fc:
                fecha_fin = snap_fc
                fecha_fuente = "snapshot"
            elif pga_ff:
                fecha_fin = pga_ff
                fecha_fuente = "pga"
            else:
                fecha_fin = ""
                fecha_fuente = None

            if snap_fa:
                fecha_inicio = snap_fa
            elif pga_fi:
                fecha_inicio = pga_fi
            else:
                fecha_inicio = ""

            existing = existing_tasks.get(task_key)
            act_calif = calificaciones.get(norm)

            if not existing:
                # to_create (solo si la fecha es futura o el nombre no calza con
                # tareas ya existentes).
                plan["to_create"].append(
                    _build_create_entry(act, list_id, fecha_inicio, fecha_fin, fecha_fuente)
                )
                continue

            # Tarea existente: evaluar si necesita update.
            # Update SOLO si hay calificacion.nota (idempotencia: el agente
            # detecta el comentario con tag [calificaciones-auto] y skipea).
            if act_calif and _needs_update_by_calificacion(act_calif):
                plan["to_update"].append(
                    _build_update_entry(existing, act_calif, list_id)
                )
            else:
                # Sin calificacion -> no es update por status. Podria haber
                # cambio de fecha, pero ese caso ya se cubre en el flujo
                # anterior; aqui no planificamos nada.
                continue

    return plan


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def sync_clickup(periodo_dir: str, dry_run: bool = False) -> int:
    """Punto de entrada principal: produce sync_plan.json.

    NO toca la API de ClickUp. Retorna exit code.
    """
    ruta_clickup = os.path.join(periodo_dir, "clickup.json")
    if not os.path.isfile(ruta_clickup):
        console.print(
            f"[bold red]ERROR:[/bold red] clickup.json no encontrado en {periodo_dir}"
        )
        console.print("    Ejecuta primero /gestionar-cursos init <URL>")
        return 1

    with open(ruta_clickup, encoding="utf-8") as f:
        clickup_data = json.load(f)

    periodo, bloque, dir_name = _resolver_periodo_dir(periodo_dir)
    folder_name = f"{periodo}-{bloque}" if bloque else periodo

    console.print(Panel.fit(
        f"[bold]ClickUp Sync — Plan-Local[/bold]\n"
        f"Periodo: {folder_name}\n"
        f"Espacio: {CLICKUP_SPACE_NAME} ({CLICKUP_SPACE_ID})\n"
        f"Cursos: {len(clickup_data.get('courses', {}))}",
        title="Resumen",
    ))

    if dry_run:
        console.print("[bold yellow]MODO DRY-RUN — sin escribir sync_plan.json[/bold yellow]\n")

    plan = _build_plan(clickup_data, periodo_dir, periodo, bloque)

    # Resumen en consola
    table = Table(title="sync_plan", show_lines=False)
    table.add_column("Seccion", style="cyan", no_wrap=True)
    table.add_column("Items", justify="right")
    for k in ("to_create", "to_update", "to_archive", "unresolved"):
        table.add_row(k, str(len(plan.get(k, []))))
    console.print(table)

    if dry_run:
        console.print(
            f"\n[bold yellow]DRY-RUN: sync_plan.json NO se escribio. "
            f"Resumen: {len(plan['to_create'])} create, "
            f"{len(plan['to_update'])} update, "
            f"{len(plan['to_archive'])} archive, "
            f"{len(plan['unresolved'])} unresolved.[/bold yellow]"
        )
        return 0

    # Escribir sync_plan.json en la raiz del periodo
    plan_path = os.path.join(periodo_dir, "sync_plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    console.print(f"\n[green]sync_plan.json escrito en {plan_path}[/green]")
    console.print(
        f"  to_create: {len(plan['to_create'])} | "
        f"to_update: {len(plan['to_update'])} | "
        f"to_archive: {len(plan['to_archive'])} | "
        f"unresolved: {len(plan['unresolved'])}"
    )
    console.print(
        "  [dim]El agente orquesta la aplicacion con use-clickup segun "
        "references/sync-flow.md[/dim]"
    )
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Producir sync_plan.json (delta Moodle->ClickUp) sin tocar la API. "
            "El agente orquesta la aplicacion con use-clickup."
        )
    )
    parser.add_argument(
        "periodo_dir",
        help="Ruta al directorio del periodo academico (ej: '2026-2-B1')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar resumen sin escribir sync_plan.json",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.periodo_dir):
        console.print(f"[bold red]ERROR:[/bold red] Directorio no encontrado: {args.periodo_dir}")
        sys.exit(1)

    rc = sync_clickup(args.periodo_dir, dry_run=args.dry_run)
    sys.exit(rc)


if __name__ == "__main__":
    main()
