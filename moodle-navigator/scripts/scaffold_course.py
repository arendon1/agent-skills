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

app = typer.Typer()
console = Console()

AGENTS_MD_TEMPLATE = """# AGENTS.md

Contexto e instrucciones para agentes de IA trabajando en esta asignatura.

## Resumen del Curso

- **Asignatura**: {course_name}
- **Código**: [PENDIENTE]
- **Docente**: [PENDIENTE] (@uniremington.edu.co)
- **Período**: 2026 Bloque 1 (Enero - Abril)
- **URL Moodle**: {moodle_url}

## Información del Docente

**Nombre**: [PENDIENTE]
**Correo**: [PENDIENTE]

**Formación**:
- [PENDIENTE]

**Canal de Teams**: [PENDIENTE]

## Estado de Inicialización

✅ **Estructura Creada**

**Fecha de creación**: {date}

## Plan de Gestión Académica

> Extraído del documento DO-FR-66 de Moodle

| Actividad | Tipo | Peso | Fecha Inicio | Fecha Fin |
|-----------|------|------|--------------|-----------|
| [PENDIENTE] | [Tipo] | 0% | DD-MM-AA | DD-MM-AA |

## Cronograma de Sesiones Sincrónicas

| # | Fecha | Hora | Tema | Enlace Sesión | Grabación |
|---|-------|------|------|---------------|-----------|
| 1 | [PENDIENTE] | 00:00pm | [Tema] | [Enlace] | [Ver] |

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
def scaffold(course_name: str, moodle_url: str):
    """
    Scaffold a new course directory with standard structure and AGENTS.md template.
    """
    from datetime import datetime
    
    # Base path is current working directory
    base_path = Path.cwd()
    course_path = base_path / course_name
    
    console.print(Panel(f"🚀 Initializing Course: [bold cyan]{course_name}[/bold cyan]", border_style="green"))

    # standard folders
    folders = [
        "Introduccion",
        "Unidad-1",
        "Unidad-2",
        "Unidad-3",
        "Transcripciones",
        "Proyectos",
        "Examenes"
    ]

    tree = Tree(f"📁 {course_name}")

    # Create directories
    if not course_path.exists():
        course_path.mkdir(parents=True)
        console.print(f"[green]Created course directory:[/green] {course_path}")
    else:
        console.print(f"[yellow]Course directory already exists:[/yellow] {course_path}")

    for folder in folders:
        folder_path = course_path / folder
        if not folder_path.exists():
            folder_path.mkdir(exist_ok=True)
            tree.add(f"✅ Created: [blue]{folder}/[/blue]")
            # Create subfolders for units
            if folder.startswith("Unidad"):
                 (folder_path / "materiales").mkdir(exist_ok=True)
                 (folder_path / "actividades").mkdir(exist_ok=True)
                 (folder_path / "notas").mkdir(exist_ok=True)
        else:
            tree.add(f"⚠️  Exists: [dim]{folder}/[/dim]")

    # Create AGENTS.md
    agents_md_path = course_path / "AGENTS.md"
    if not agents_md_path.exists():
        content = AGENTS_MD_TEMPLATE.format(
            course_name=course_name,
            moodle_url=moodle_url,
            date=datetime.now().strftime("%d de %B de %Y")
        )
        with open(agents_md_path, "w", encoding="utf-8") as f:
            f.write(content)
        tree.add("📄 [bold green]Created: AGENTS.md[/bold green]")
    else:
        tree.add("📄 [dim]Exists: AGENTS.md[/dim]")

    console.print(tree)
    console.print("\n[bold green]✨ Course setup complete![/bold green] Next step: Use [bold cyan]moodle-navigator[/bold cyan] to populate data.")

if __name__ == "__main__":
    app()
