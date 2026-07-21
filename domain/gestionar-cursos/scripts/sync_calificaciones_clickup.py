"""Sincronizar calificaciones Moodle → ClickUp.

Sincronización entre snapshot.json (calificaciones Moodle extraídas
por `cli_calificaciones.py`) y las tareas en ClickUp del curso.

Por cada tarea con `calificacion.estado in (Aprobado, Calificado, Reprobado)`
y nota numérica:
  1. PUT /task/{id} con status="calificado" (closed) — la marca como hecha.
  2. POST /task/{id}/comment con detalle de la nota.

Si la tarea ya está en status "calificado" y ya tiene un comentario de
esta sync, la salta (idempotencia).

Uso:
    uv run python sync_calificaciones_clickup.py <CARPETA_CURSO>
    uv run python sync_calificaciones_clickup.py <CARPETA_CURSO> --dry-run

Parámetros:
    CARPETA_CURSO    Carpeta raíz del curso (con _cache/snapshot.json
                     y clickup.json arriba en 2 niveles)
    --dry-run        Solo listar las tareas que se actualizarían

Notas:
- La API de PUT /task/{id} acepta el NOMBRE del status (case-insensitive),
  NO el status_id. El script resuelve el nombre vía GET /space/{id}.
- El status "calificado" existe solo en spaces donde el docente lo creó.
  Si no existe, se reporta con lista de statuses disponibles.
- El comentario lleva el tag [calificaciones-auto] para que `tiene_comentario_sync`
  detecte re-sincronizaciones sin duplicar.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

from rich.console import Console

# Resolver el path a use-clickup/scripts dinámicamente: probamos varias
# ubicaciones porque el skill puede vivir en:
#   - ~/.agents/skills/{gestionar-cursos,use-clickup}/scripts/  (producción)
#   - agent-skills/domain/{gestionar-cursos,use-clickup}/scripts/  (source)
_here = os.path.dirname(os.path.abspath(__file__))
for _candidate in [
    os.path.normpath(os.path.join(_here, "..", "..", "use-clickup", "scripts")),
    os.path.normpath(os.path.join(_here, "..", "use-clickup", "scripts")),
    os.path.expanduser("~/.agents/skills/use-clickup/scripts"),
]:
    if os.path.isdir(_candidate) and _candidate not in sys.path:
        sys.path.insert(0, _candidate)
        break
else:
    raise SystemExit(
        "No se encontró el módulo `client` de use-clickup. "
        "Verifica que use-clickup esté instalado junto a gestionar-cursos."
    )

from client import get_client

console = Console()

CLICKUP_SPACE_ID = "901311224662"
STATUS_CALIFICADO = "calificado"
COMMENT_TAG = "[calificaciones-auto]"


def get_status_name(client, space_id: str, status_name: str) -> str:
    """Verifica que el status existe en el space y devuelve el nombre canónico.

    La API de PUT /task/{id} acepta el NOMBRE del status, no el ID
    (a diferencia de otros campos). Devolvemos el nombre tal cual
    aparece en space.statuses[].status para case-sensitivity estricto.
    """
    resp = client.get(f"/space/{space_id}")
    space = resp.json()
    for s in space.get("statuses", []):
        if s["status"].lower() == status_name.lower():
            return s["status"]
    raise RuntimeError(
        f"Status '{status_name}' no encontrado en space {space_id}. "
        f"Disponibles: {[s['status'] for s in space.get('statuses', [])]}"
    )


def resolver_paths(ruta_curso: str) -> tuple[str, str, str]:
    """Devuelve (curso_key, snapshot_path, clickup_json_path).

    Lee el course ID de AGENTS.md para armar el CURSO_{id} que se usa
    como clave en clickup.json. Asume que clickup.json vive 1 nivel
    arriba de la carpeta de curso.
    """
    agents_path = os.path.join(ruta_curso, "AGENTS.md")
    curso_key = None
    if os.path.isfile(agents_path):
        with open(agents_path) as f:
            text = f.read()
        m = re.search(r"course/view\.php\?id=(\d+)", text)
        if m:
            curso_key = f"CURSO_{m.group(1)}"

    snapshot_path = os.path.join(ruta_curso, "_cache", "snapshot.json")
    clickup_json = os.path.join(
        os.path.dirname(os.path.normpath(ruta_curso)), "clickup.json"
    )
    return curso_key, snapshot_path, clickup_json


def tarea_ya_calificada(client, task_id: str) -> bool:
    """Verifica si la tarea ya está en status 'calificado'."""
    resp = client.get(f"/task/{task_id}")
    task = resp.json()
    status = task.get("status", {}).get("status", "").lower()
    return status == STATUS_CALIFICADO


def tiene_comentario_sync(client, task_id: str) -> bool:
    """Verifica si ya dejamos un comentario automático en la tarea."""
    resp = client.get(f"/task/{task_id}/comment")
    comments = resp.json().get("comments", [])
    return any(COMMENT_TAG in (c.get("comment_text", "") or "") for c in comments)


def update_status(client, task_id: str, status_name: str) -> dict:
    """Actualiza el status de la tarea (usa el NOMBRE del status)."""
    resp = client.put(f"/task/{task_id}", json={"status": status_name})
    if resp.status_code != 200:
        raise RuntimeError(
            f"Error actualizando status de {task_id}: {resp.status_code} {resp.text[:200]}"
        )
    return resp.json()


def post_comentario(client, task_id: str, texto: str) -> dict:
    """Deja un comentario en la tarea."""
    resp = client.post(
        f"/task/{task_id}/comment",
        json={"comment_text": texto, "notify_all": False},
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Error dejando comentario en {task_id}: {resp.status_code} {resp.text[:200]}"
        )
    return resp.json()


def format_comentario(actividad: dict, curso_nombre: str) -> str:
    """Formatea el comentario con la calificación."""
    c = actividad["calificacion"]
    nota = c.get("nota") or "—"
    rango = c.get("rango") or "—"
    porcentaje = c.get("porcentaje") or "—"
    aporte = c.get("aporte_curso") or "0,00 %"
    estado = c.get("estado", "?")
    actualizado = c.get("actualizado", "")[:19]
    return (
        f"{COMMENT_TAG} Calificación sincronizada desde Moodle\n\n"
        f"- **Curso:** {curso_nombre}\n"
        f"- **Actividad:** {actividad.get('nombre', '?')}\n"
        f"- **Nota:** {nota} / {rango} ({porcentaje})\n"
        f"- **Estado:** {estado}\n"
        f"- **Aporte al curso:** {aporte}\n"
        f"- **Capturado:** {actualizado}\n"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Sincronizar calificaciones Moodle → ClickUp"
    )
    parser.add_argument(
        "ruta_curso",
        help="Carpeta raíz del curso (con _cache/snapshot.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo listar las tareas que se actualizarían, sin hacer cambios",
    )
    args = parser.parse_args()

    ruta_curso = os.path.abspath(args.ruta_curso)
    if not os.path.isdir(ruta_curso):
        raise SystemExit(f"Carpeta no existe: {ruta_curso}")

    curso_key, snapshot_path, clickup_json = resolver_paths(ruta_curso)
    if not curso_key:
        raise SystemExit(f"No se pudo extraer course ID de {ruta_curso}/AGENTS.md")
    if not os.path.isfile(snapshot_path):
        raise SystemExit(f"No se encontró snapshot.json en {snapshot_path}")
    if not os.path.isfile(clickup_json):
        raise SystemExit(f"No se encontró clickup.json en {clickup_json}")

    console.print(f"[bold blue]Curso:[/bold blue] {ruta_curso}")
    console.print(f"[bold blue]Course key:[/bold blue] {curso_key}")
    if args.dry_run:
        console.print("[bold yellow]MODO DRY-RUN — sin cambios en ClickUp[/bold yellow]\n")

    client = get_client()

    # 1) Cargar clickup.json para resolver list + tareas
    with open(clickup_json) as f:
        clickup_data = json.load(f)
    curso = clickup_data["courses"].get(curso_key)
    if not curso:
        raise SystemExit(f"{curso_key} no encontrado en {clickup_json}")
    list_name = curso["list_name"]
    tasks_map = curso.get("tasks", {})

    # 2) Cargar snapshot.json para leer calificaciones
    with open(snapshot_path) as f:
        snapshot = json.load(f)

    # 3) Resolver status "calificado" del space Universidad
    status_name = get_status_name(client, CLICKUP_SPACE_ID, STATUS_CALIFICADO)
    print(f"Status '{STATUS_CALIFICADO}' → '{status_name}'\n")

    # 4) Encontrar tareas calificadas: cruzar por nombre snapshot ↔ clickup
    actualizadas = []
    saltadas = []

    for key, act in snapshot["actividades"].items():
        cal = act.get("calificacion")
        if not cal or not cal.get("nota"):
            continue  # sin calificación numérica → no tocar
        if cal.get("estado") not in ("Aprobado", "Calificado", "Reprobado"):
            continue  # pendiente → no tocar

        nombre = act.get("nombre", "")
        # Resolver task_id por nombre exacto
        task_id = tasks_map.get(nombre, {}).get("id") if isinstance(tasks_map.get(nombre), dict) else None
        if not task_id:
            # buscar por match flexible
            for task_name, task_info in tasks_map.items():
                if task_name.lower() in nombre.lower() or nombre.lower() in task_name.lower():
                    task_id = task_info.get("id") if isinstance(task_info, dict) else None
                    if task_id:
                        break
        if not task_id:
            print(f"⚠ No se encontró task_id para: {nombre}")
            continue

        # Verificar estado actual
        ya_calificada = tarea_ya_calificada(client, task_id)
        ya_comentario = tiene_comentario_sync(client, task_id)

        if ya_calificada and ya_comentario:
            print(f"= {nombre:35s}  ya calificada y con comentario — skip")
            saltadas.append(nombre)
            continue

        if args.dry_run:
            accion = []
            if not ya_calificada:
                accion.append(f"status → {status_name}")
            if not ya_comentario:
                accion.append("comentario")
            print(f"· {nombre:35s}  DRY: {', '.join(accion) or 'noop'}")
            continue

        # 5a) Actualizar status si no está ya
        if not ya_calificada:
            update_status(client, task_id, status_name)
            print(f"✓ {nombre:35s}  status → {status_name}")
        else:
            print(f"= {nombre:35s}  status ya era {status_name}")

        # 5b) Dejar comentario
        texto = format_comentario(act, list_name)
        post_comentario(client, task_id, texto)
        print(f"  + comentario: nota={cal.get('nota')}, aporte={cal.get('aporte_curso')}")

        actualizadas.append(nombre)

    print()
    print(f"Actualizadas: {len(actualizadas)}")
    print(f"Saltadas (ya sincronizadas): {len(saltadas)}")
    if actualizadas:
        print()
        print("Tareas actualizadas en ClickUp:")
        for n in actualizadas:
            print(f"  - {n}")


if __name__ == "__main__":
    main()
