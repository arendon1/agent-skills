# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich",
# ]
# ///

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

REQUIRED_FOLDERS = [
    "Introduccion",
    "Unidad-1/materiales",
    "Unidad-1/actividades",
    "Unidad-1/notas",
    "Transcripciones",
    "Proyectos",
    "Examenes",
]

REQUIRED_FILES = [
    "AGENTS.md",
    "sitemap.md",
    "README.md",
]

def check_metadata(agents_md_content):
    issues = []
    if "[PENDIENTE]" in agents_md_content:
        issues.append("Contiene campos '[PENDIENTE]'")
    if "COURSE_ID" not in agents_md_content:
        issues.append("Falta COURSE_ID")
    return issues

def verify_course(course_path):
    path = Path(course_path)
    if not path.exists():
        console.print(f"[red]Error: El directorio {course_path} no existe.[/red]")
        return False

    table = Table(title=f"Verificación de Workspace: {path.name}")
    table.add_column("Elemento", style="cyan")
    table.add_column("Estado", style="magenta")
    table.add_column("Detalles", style="yellow")

    # Check Folders
    for folder in REQUIRED_FOLDERS:
        f_path = path / folder
        status = "✅ OK" if f_path.is_dir() else "❌ Falta"
        table.add_row(f"Carpeta: {folder}", status, "")

    # Check Files
    for file in REQUIRED_FILES:
        f_path = path / file
        status = "✅ OK" if f_path.is_file() else "❌ Falta"
        details = ""
        if f_path.name == "AGENTS.md" and f_path.is_file():
            content = f_path.read_text(encoding="utf-8")
            issues = check_metadata(content)
            if issues:
                status = "⚠️  Warn"
                details = ", ".join(issues)
        table.add_row(f"Archivo: {file}", status, details)

    console.print(table)
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[yellow]Uso: python verify_workspace.py <ruta_del_curso>[/yellow]")
        sys.exit(1)

    success = verify_course(sys.argv[1])
    sys.exit(0 if success else 1)
