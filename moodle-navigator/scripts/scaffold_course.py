# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich",
#     "typer",
# ]
# ///

import typer
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from pathlib import Path
from datetime import datetime
import json

app = typer.Typer()
console = Console()


def force_download_url(url: str) -> str:
    """Ensure Moodle file links have the forcedownload=1 parameter."""
    if "pluginfile.php" in url and "forcedownload=1" not in url:
        return f"{url}&forcedownload=1" if "?" in url else f"{url}?forcedownload=1"
    return url


AGENTS_MD_TEMPLATE = """# AGENTS.md

Contexto e instrucciones para agentes de IA trabajando en esta asignatura.

## Resumen del Curso

- **Asignatura**: {course_name}
- **Código**: {course_code}
- **Docente**: {teacher_name} ({teacher_email})
- **Período**: {year}-{semester} Bloque {block}
- **URL Moodle**: {moodle_url}

## Información del Docente

**Nombre**: {teacher_name}
**Correo**: {teacher_email}

**Canal de Teams**: {teams_link}

## Estado de Inicialización

✅ **Estructura Creada**
📅 **Fecha de creación**: {date}

## Plan de Gestión Académica (DO-FR-66)

| Actividad | Tipo | Peso | Fecha Inicio | Fecha Fin |
|-----------|------|------|--------------|-----------|
{pga_table}

## Cronograma de Sesiones Sincrónicas

| # | Fecha | Hora | Tema | Enlace Sesión | Grabación |
|---|-------|------|------|---------------|-----------|
{cronograma_table}

## Materiales del Curso

### Documentos Globales (Introducción)

| Documento | Tipo | URL Moodle | Estado |
|-----------|------|------------|--------|
| Módulo | PDF | [URL] | 📥 Pendiente |
| Microcurrículo | PDF | [URL] | 📥 Pendiente |

## Instrucciones para el Agente

### Protocolo de Actuación
1.  **Completar información**: Usar `moodle-navigator` para extraer datos reales de Moodle y reemplazar los campos [PENDIENTE].
2.  **Sincronizar**: Mantener este archivo actualizado con cualquier cambio en el curso.
"""


@app.command()
def scaffold(
    course_name: str,
    moodle_url: str,
    course_code: str = "[PENDIENTE]",
    teacher_name: str = "[PENDIENTE]",
    teacher_email: str = "[PENDIENTE]",
    year: str = str(datetime.now().year),
    semester: str = "1",
    block: str = "1",
    teams_link: str = "[PENDIENTE]",
    pga_data: str = "",  # JSON string of activities
    cronograma_data: str = "",  # JSON string of sessions
    sitemap_data: str = "",  # JSON string of Moodle sections/links
    force: bool = False,
):
    """
    Scaffold a new course directory with deep metadata and standard structure.
    """
    base_path = Path.cwd()
    course_path = base_path / course_name

    console.print(
        Panel(
            f"🚀 Initializing Course: [bold cyan]{course_name}[/bold cyan]",
            border_style="green",
        )
    )

    # Parse PGA and Cronograma
    pga_table = "| [PENDIENTE] | [Tipo] | 0% | DD-MM-AA | DD-MM-AA |"
    if pga_data:
        try:
            activities = json.loads(pga_data)
            pga_table = "\n".join(
                [
                    f"| {a['name']} | {a.get('type', 'N/A')} | {a.get('weight', '0%')} | {a.get('start', 'N/A')} | {a.get('end', 'N/A')} |"
                    for a in activities
                ]
            )
        except Exception:
            pass

    cronograma_table = "| 1 | [PENDIENTE] | 00:00pm | [Tema] | [Enlace] | [Ver] |"
    if cronograma_data:
        try:
            sessions = json.loads(cronograma_data)
            cronograma_table = "\n".join(
                [
                    f"| {i + 1} | {s['date']} | {s['time']} | {s.get('topic', 'N/A')} | {s.get('link', '[Enlace]')} | {s.get('recording', '[Ver]')} |"
                    for i, s in enumerate(sessions)
                ]
            )
        except Exception:
            pass

    # Parse Sitemap
    initial_sitemap = [
        f"# Course Sitemap: {course_name}",
        "",
        "## 🌐 Moodle Sections (Permanent Links)",
        "> Autoridad: Moodle",
        "",
    ]
    if sitemap_data:
        try:
            links = json.loads(sitemap_data)
            for item in links:
                url = force_download_url(item["url"])
                level = item.get("level", 0)
                indent = "  " * level
                initial_sitemap.append(f"{indent}- [{item['name']}]({url})")
        except Exception:
            pass

    # Standard folders
    folders = [
        "Introduccion",
        "Unidad-1",
        "Unidad-2",
        "Unidad-3",
        "Transcripciones",
        "Proyectos",
        "Examenes",
    ]

    folder_descriptions = {
        "Introduccion": "Contiene los documentos globales del curso, presentaciones, plan académico (DO-FR-66) y cronogramas.",
        "Unidad-1": "Materiales, notas y actividades correspondientes a la Unidad 1.",
        "Unidad-2": "Materiales, notas y actividades correspondientes a la Unidad 2.",
        "Unidad-3": "Materiales, notas y actividades correspondientes a la Unidad 3.",
        "Transcripciones": "Archivos transcritos de las sesiones sincrónicas o videos de clase.",
        "Proyectos": "Especificaciones, avances, y entregas finales de los proyectos.",
        "Examenes": "Preparación, enunciados y retroalimentación de los exámenes.",
    }

    tree = Tree(f"📁 {course_name}")

    if not course_path.exists():
        course_path.mkdir(parents=True)
        console.print(f"[green]Created course directory:[/green] {course_path}")

    for folder in folders:
        folder_path = course_path / folder
        if not folder_path.exists():
            folder_path.mkdir(exist_ok=True)
            tree.add(f"✅ Created: [blue]{folder}/[/blue]")

            desc = folder_descriptions.get(folder, f"Directorio para {folder}")
            with open(folder_path / "README.md", "w", encoding="utf-8") as f:
                f.write(f"# {folder}\n\n{desc}\n")

            if folder.startswith("Unidad"):
                for subf, subdesc in [
                    (
                        "materiales",
                        "Recursos educativos proporcionados por el docente (PDFs, lecturas, etc).",
                    ),
                    ("actividades", "Tareas, talleres y entregables a desarrollar."),
                    ("notas", "Apuntes personales y resúmenes de estudio."),
                ]:
                    sub_path = folder_path / subf
                    sub_path.mkdir(exist_ok=True)
                    with open(sub_path / "README.md", "w", encoding="utf-8") as f:
                        f.write(f"# {subf.capitalize()}\n\n{subdesc}\n")
        else:
            tree.add(f"⚠️  Exists: [dim]{folder}/[/dim]")

    # Create AGENTS.md
    agents_md_path = course_path / "AGENTS.md"
    if not agents_md_path.exists() or force:
        content = AGENTS_MD_TEMPLATE.format(
            course_name=course_name,
            course_code=course_code,
            moodle_url=moodle_url,
            teacher_name=teacher_name,
            teacher_email=teacher_email,
            year=year,
            semester=semester,
            block=block,
            teams_link=teams_link,
            pga_table=pga_table,
            cronograma_table=cronograma_table,
            date=datetime.now().strftime("%d de %B de %Y"),
        )
        with open(agents_md_path, "w", encoding="utf-8") as f:
            f.write(content)
        tree.add("📄 [bold green]Created: AGENTS.md[/bold green]")
    else:
        tree.add("📄 [dim]Exists: AGENTS.md (Skip)[/dim]")

    # Create initial sitemap.md
    sitemap_path = course_path / "sitemap.md"
    if not sitemap_path.exists() or force:
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write("\n".join(initial_sitemap))
        tree.add("📄 [bold green]Created: sitemap.md[/bold green]")

    # Create AI Rules for the workspace (Vendor Agnostic)
    rule_content = """---
description: Estructura de carpetas y reglas del curso
globs: *
---
# Reglas de Estructura del Curso

Este es un curso inicializado desde Moodle. Debes respetar rigurosamente la siguiente estructura de carpetas al crear, mover o procesar archivos:

- `Introduccion/`: Contiene documentos globales, presentaciones, plan académico (DO-FR-66) y cronogramas.
- `Unidad-X/`: Materiales, notas y actividades de la Unidad X.
  - `Unidad-X/materiales/`: Recursos educativos del docente (PDFs, lecturas).
  - `Unidad-X/actividades/`: Tareas, talleres y entregables a desarrollar.
  - `Unidad-X/notas/`: Apuntes personales y resúmenes de estudio.
- `Transcripciones/`: Transcripciones de sesiones sincrónicas o videos.
- `Proyectos/`: Especificaciones, avances, y entregas de proyectos.
- `Examenes/`: Preparación y retroalimentación de exámenes.

**REGLA CRÍTICA**: Nunca guardes archivos sueltos en la raíz del curso. Clasifica todo material descargado o generado en su carpeta correspondiente según este esquema.
"""

    # Deploy rules to multiple known agent folders to remain vendor-agnostic
    agent_rule_dirs = [
        ".cursor/rules",
        ".gemini/rules",
        ".agents/rules",
        ".github/copilot-instructions",
    ]

    for r_dir in agent_rule_dirs:
        rules_dir = course_path / r_dir
        rules_dir.mkdir(parents=True, exist_ok=True)

        # Use .mdc for cursor, .md for others
        ext = ".mdc" if "cursor" in r_dir else ".md"
        rule_path = rules_dir / f"moodle-folders{ext}"

        if not rule_path.exists() or force:
            with open(rule_path, "w", encoding="utf-8") as f:
                f.write(rule_content)
            tree.add(
                f"📄 [bold green]Created: {r_dir}/moodle-folders{ext}[/bold green]"
            )

    console.print(tree)
    console.print("\n[bold green]✨ Course setup complete![/bold green]")


if __name__ == "__main__":
    app()
