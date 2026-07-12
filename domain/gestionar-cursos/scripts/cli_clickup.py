#!/usr/bin/env python3
"""
CLI: /gestionar-cursos clickup-sync <PERIODO_DIR>

Sincroniza estructura local de cursos con ClickUp:
1. Resuelve folder/list IDs en el espacio "Universidad"
2. Crea tareas para actividades pendientes
3. Actualiza AGENTS.md con CLICKUP_LIST_ID

Uso:
    cd gestionar-cursos/scripts
    uv run python cli_clickup.py "C:/Users/.../Universidad/2026-2-B1"
    uv run python cli_clickup.py "C:/Users/.../Universidad/2026-2-B1" --dry-run
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

# ClickUp operations are delegated to the use-clickup skill at agent level.
# See SKILL.md for instructions on how the agent orchestrates between skills.

CLICKUP_SPACE_ID = "901311224662"
CLICKUP_SPACE_NAME = "Universidad"

SUPPORT_KEYWORDS = {
    "grupal": ["grupal", "grupo", "equipo", "colaborativo"],
    "entregable": ["entregable", "subir", "archivo", "enlace", "entregar"],
    "lectura": ["lectura", "leer"],
    "repaso": ["repaso", "estudiar", "preparar"],
    "documento": ["documento", "informe", "ensayo", "redact"],
    "investigar": ["investigar", "buscar", "fuentes"],
    "practica": ["practica", "ejercicio", "código", "laboratorio", "código"],
    "exposicion": ["exposicion", "presentación", "exponer", "sustent"],
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
    elif any(kw in nombre_lower for kw in ["cuestionario", "prueba", "quiz", "examen", "lección"]):
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
    elif valor_num > 0:
        tags.append("evaluable")
    # default: assume evaluable if has valor
    if "evaluable" not in tags and "no-evaluable" not in tags:
        tags.append("evaluable" if valor_num > 0 else "no-evaluable")

    # --- Soporte ---
    for tag, keywords in SUPPORT_KEYWORDS.items():
        if any(kw in nombre_lower for kw in keywords):
            if tag not in tags:
                tags.append(tag)

    return tags, prioridad


# ---------------------------------------------------------------------------
# ClickUp ID resolution
# ---------------------------------------------------------------------------

def _resolver_folder(client, space_id: str, folder_name: str) -> str:
    """Find folder by name or create it. Returns folder ID."""
    resp = client.get(f"/space/{space_id}/folder?archived=false")
    if resp.status_code != 200:
        raise RuntimeError(f"Error listando folders: {resp.status_code} {resp.text}")
    folders = resp.json().get("folders", [])
    for f in folders:
        if f["name"] == folder_name:
            return f["id"]

    resp = client.post(f"/space/{space_id}/folder", json={"name": folder_name})
    if resp.status_code != 200:
        raise RuntimeError(f"Error creando folder '{folder_name}': {resp.status_code} {resp.text}")
    fid = resp.json()["id"]
    console.print(f"    [green]+Folder creado:[/green] {folder_name} ({fid})")
    return fid


def _resolver_list(client, folder_id: str, list_name: str) -> str:
    """Find list by name or create it. Returns list ID."""
    existing = view_lists(folder_id=folder_id)
    for lst in existing:
        if lst["name"] == list_name:
            return lst["id"]

    result = create_list(folder_id=folder_id, name=list_name)
    lid = result["id"]
    console.print(f"    [green]+Lista creada:[/green] {list_name} ({lid})")
    return lid


# ---------------------------------------------------------------------------
# PGA.md parsing
# ---------------------------------------------------------------------------

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


def _normalizar_nombre(nombre: str) -> str:
    """Quita sufijos '(X%)' / '(N/A)' del nombre para matching snapshot↔PGA."""
    return re.sub(r"\s*\([^)]*%[^)]*\)\s*$", "", nombre).strip()


def _parsear_snapshot(ruta_curso: str) -> dict[str, dict[str, str]]:
    """Lee _cache/snapshot.json y devuelve {nombre_normalizado: {fecha_apertura, fecha_cierre}}.

    Fuente de verdad de fechas reales de Moodle (ver "Fuente de Verdad de
    Fechas" en SKILL.md). Devuelve {} si la snapshot no existe o no tiene fechas.
    """
    path = os.path.join(ruta_curso, "_cache", "snapshot.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    fechas: dict[str, dict[str, str]] = {}
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


# ---------------------------------------------------------------------------
# AGENTS.md update
# ---------------------------------------------------------------------------

def _actualizar_agents_md(ruta_curso: str, list_id: str):
    """Replace [PENDIENTE] CLICKUP_LIST_ID with actual ID."""
    agents_path = os.path.join(ruta_curso, "AGENTS.md")
    if not os.path.isfile(agents_path):
        console.print(f"    [yellow]WARN:[/yellow] AGENTS.md no encontrado en {ruta_curso}")
        return

    with open(agents_path, encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r"CLICKUP_LIST_ID\]:\s*\[PENDIENTE\]",
        f"CLICKUP_LIST_ID]: {list_id}",
        content,
    )
    new_content = re.sub(
        r"CLICKUP_LIST_ID\]:\s*null",
        f"CLICKUP_LIST_ID]: {list_id}",
        new_content,
    )

    if new_content != content:
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        console.print(f"    [dim]AGENTS.md actualizado con list_id[/dim]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _resolver_periodo_dir(periodo_dir: str) -> tuple[str, str, str]:
    """Extract periodo and bloque from path like .../2026-2-B1."""
    dir_name = os.path.basename(os.path.abspath(periodo_dir))
    match = re.match(r"(\d{4}-\d)(?:-(B\d+))?", dir_name)
    if not match:
        return dir_name, dir_name, ""
    periodo = match.group(1)
    bloque = match.group(2) or ""
    return periodo, bloque, dir_name


def sync_clickup(periodo_dir: str, dry_run: bool = False):
    """Main entry point: syncs everything in periodo_dir with ClickUp."""
    ruta_clickup = os.path.join(periodo_dir, "clickup.json")
    if not os.path.isfile(ruta_clickup):
        console.print(f"[bold red]ERROR:[/bold red] clickup.json no encontrado en {periodo_dir}")
        console.print("    Ejecuta primero /gestionar-cursos init <URL>")
        return

    with open(ruta_clickup, encoding="utf-8") as f:
        clickup_data = json.load(f)

    periodo, bloque, dir_name = _resolver_periodo_dir(periodo_dir)
    folder_name = f"{periodo}-{bloque}" if bloque else periodo
    courses = clickup_data.get("courses", {})
    if not courses:
        console.print("[yellow]No hay cursos en clickup.json[/yellow]")
        return

    console.print(Panel.fit(
        f"[bold]ClickUp Sync[/bold]\n"
        f"Período: {folder_name}\n"
        f"Espacio: {CLICKUP_SPACE_NAME} ({CLICKUP_SPACE_ID})\n"
        f"Cursos: {len(courses)}",
        title="Resumen",
    ))

    if dry_run:
        console.print("[bold yellow]MODO DRY-RUN — sin cambios en ClickUp[/bold yellow]\n")

    # --- Step 1: resolve folder ---
    console.print("[bold cyan][1/3][/bold cyan] Resolviendo folder...")
    folder_id = None
    if not dry_run:
        client = get_client()
        folder_id = _resolver_folder(client, CLICKUP_SPACE_ID, folder_name)
        clickup_data["folder"]["id"] = folder_id
        console.print(f"    Folder: {folder_name} → {folder_id}")
    else:
        console.print(f"    Folder: {folder_name} (dry-run)")

    # --- Step 2: resolve each course list ---
    console.print("\n[bold cyan][2/3][/bold cyan] Resolviendo listas de cursos...")
    list_map = {}  # course_key → list_id
    total_tasks_created = 0

    for course_key, course_info in courses.items():
        list_name = course_info.get("list_name", course_key)
        list_id = course_info.get("list_id")

        console.print(f"\n  [bold]{course_key}[/bold] — {list_name}")

        if not list_id and not dry_run:
            list_id = _resolver_list(client, folder_id, list_name)
            course_info["list_id"] = list_id
            console.print(f"    list_id → {list_id}")
        elif not list_id and dry_run:
            console.print("    list_id: [PENDIENTE] (dry-run)")
        else:
            console.print(f"    list_id: {list_id} (existente)")

        list_map[course_key] = list_id

        # Update AGENTS.md
        if list_id and not dry_run:
            ruta_curso = _encontrar_ruta_curso(periodo_dir, course_key)
            if ruta_curso:
                _actualizar_agents_md(ruta_curso, list_id)

    # --- Step 3: create tasks for each course ---
    console.print("\n[bold cyan][3/3][/bold cyan] Sincronizando tareas...")

    for course_key, course_info in courses.items():
        list_id = course_info.get("list_id")
        if not list_id:
            console.print(f"\n  [yellow][saltando][/yellow] {course_key} — sin list_id")
            continue

        list_name = course_info.get("list_name", course_key)
        existing_tasks_raw = course_info.get("tasks", {})
        existing_tasks: dict[str, dict] = {}
        for k, v in existing_tasks_raw.items():
            existing_tasks[_task_key(k)] = v
        course_info["tasks"] = existing_tasks

        ruta_curso = _encontrar_ruta_curso(periodo_dir, course_key)
        if not ruta_curso:
            console.print(f"  [yellow]WARN:[/yellow] {course_key} — carpeta de curso no encontrada")
            continue

        pga_path = os.path.join(ruta_curso, "PGA.md")
        actividades = _parsear_pga_md(pga_path)
        if not actividades:
            console.print(f"  [dim]{course_key}: PGA.md sin actividades[/dim]")
            continue

        # Fuente de verdad: fechas reales extraídas de Moodle por `estado`.
        # Ver "Fuente de Verdad de Fechas" en SKILL.md.
        snapshot_fechas = _parsear_snapshot(ruta_curso)
        if snapshot_fechas:
            console.print(f"    [dim]snapshot: {len(snapshot_fechas)} actividades con fechas reales[/dim]")
        else:
            console.print(f"    [yellow]sin snapshot — usando fechas del PGA (pueden estar desactualizadas)[/yellow]")

        console.print(f"\n  [bold]{course_key}[/bold] — {len(actividades)} actividades en PGA")

        for act in actividades:
            nombre_act = act["actividad"]
            task_key = _task_key(nombre_act)

            # Reconciliar fechas: snapshot (Moodle real) es autoritativa;
            # PGA es respaldo para actividades no visitables o sin snapshot.
            norm = _normalizar_nombre(nombre_act)
            snap = snapshot_fechas.get(norm, {})
            fecha_inicio = snap.get("fecha_apertura") or act.get("fecha_inicio", "")
            fecha_fin = snap.get("fecha_cierre") or act.get("fecha_fin", "")

            if task_key in existing_tasks:
                # Check if start or due DATE changed (compare day-level only
                # to avoid spurious updates from time-precision mismatch:
                # clickup.json stores '2026-07-12T23:59', PGA stores '2026-07-12').
                existing_due = existing_tasks[task_key].get("due_date", "")
                existing_start = existing_tasks[task_key].get("start_date", "")
                fin_day = fecha_fin[:10] if fecha_fin else ""
                ini_day = fecha_inicio[:10] if fecha_inicio else ""
                ex_due_day = existing_due[:10] if existing_due else ""
                ex_start_day = existing_start[:10] if existing_start else ""
                changed = (fin_day and ex_due_day != fin_day) or \
                          (ini_day and ex_start_day != ini_day)
                if changed:
                    if not dry_run:
                        update_task(
                            task_id=existing_tasks[task_key]["id"],
                            due_date=fecha_fin or None,
                            start_date=fecha_inicio or None,
                            name=nombre_act,
                        )
                        existing_tasks[task_key]["due_date"] = fecha_fin
                        existing_tasks[task_key]["start_date"] = fecha_inicio
                    src = "snapshot" if snap else "PGA"
                    console.print(f"    [cyan]↻ actualizado ({src}):[/cyan] {nombre_act} → {fecha_inicio or '-'}…{fecha_fin}")
                else:
                    console.print(f"    [dim]✓ {nombre_act} (existente)[/dim]")
                continue

            # New task
            tags, prioridad = _clasificar_actividad(nombre_act, act["valor"])
            descripcion = (
                f"## {nombre_act}\n\n"
                f"- **Valor:** {act['valor']}\n"
                f"- **Unidad:** {act['unidad']}\n"
                f"- **Semana:** {act['semana']}\n"
                f"- **Inicio:** {fecha_inicio}\n"
                f"- **Fin:** {fecha_fin}\n"
            )

            if dry_run:
                console.print(
                    f"    [green]+ (dry) {nombre_act}[/green] "
                    f"| tags: {tags} | prioridad: {prioridad} | start: {fecha_inicio or '-'} | due: {fecha_fin}"
                )
                continue

            try:
                result = create_task(
                    list_id=list_id,
                    name=nombre_act,
                    description=descripcion,
                    due_date=fecha_fin or None,
                    start_date=fecha_inicio or None,
                    tags=tags,
                    priority=prioridad,
                )
                task_id = result.get("id", "")
                existing_tasks[task_key] = {
                    "id": task_id,
                    "due_date": fecha_fin,
                    "start_date": fecha_inicio,
                    "tags": tags,
                }
                total_tasks_created += 1
                console.print(
                    f"    [green]+ {nombre_act}[/green] "
                    f"| {prioridad} | start: {fecha_inicio or '-'} | {fecha_fin or 'sin fecha'}"
                )
            except Exception as e:
                console.print(f"    [red]ERROR creando '{nombre_act}':[/red] {e}")

    # --- Save updated clickup.json ---
    if not dry_run:
        with open(ruta_clickup, "w", encoding="utf-8") as f:
            json.dump(clickup_data, f, indent=2, ensure_ascii=False)
        console.print(f"\n[green]clickup.json actualizado[/green]")

    # --- Summary ---
    console.print(f"\n[bold green]Sincronización completa.[/bold green]")
    console.print(f"  Tareas nuevas: {total_tasks_created}")

    if dry_run:
        console.print("  [bold yellow]Modo dry-run — sin cambios reales[/bold yellow]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_key(nombre: str) -> str:
    """Generate stable key for a task from its name."""
    return re.sub(r"[^a-z0-9_]", "_", nombre.lower().strip())[:60]


def _encontrar_ruta_curso(periodo_dir: str, course_key: str) -> Optional[str]:
    """Find course directory inside periodo_dir.

    Matching priority:
      1. Moodle course ID: course_key like 'CURSO_14822' ⟶ AGENTS.md URL 'id=14822'
      2. Academic CODIGO: AGENTS.md '**CODIGO**: 2607B04G1' ⟶ unique per course
    """
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

        # 1) Match by Moodle ID in URL (most reliable, unique per course)
        if moodle_id:
            url_m = re.search(r"id=(\d+)", content)
            if url_m and url_m.group(1) == moodle_id:
                return entry.path

        # 2) Fallback: match by CODIGO
        if codigo:
            code_m = re.search(r"\*\*CODIGO\*\*:\s*(\S+)", content)
            if code_m and (course_key.endswith(code_m.group(1)) or course_key == code_m.group(1)):
                return entry.path
        else:
            code_m = re.search(r"\*\*CODIGO\*\*:\s*(\S+)", content)
            if code_m and code_m.group(1) in course_key:
                return entry.path
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Sincroniza cursos locales con ClickUp (resuelve IDs, crea tareas)"
    )
    parser.add_argument(
        "periodo_dir",
        help="Ruta al directorio del período académico (ej: '2026-2-B1')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Previsualizar sin modificar ClickUp",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.periodo_dir):
        console.print(f"[bold red]ERROR:[/bold red] Directorio no encontrado: {args.periodo_dir}")
        sys.exit(1)

    sync_clickup(args.periodo_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
