# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich",
# ]
# ///

from pathlib import Path


def deploy():
    # Detect workspace root (assuming we are inside /skills/moodle-navigator/scripts)
    skill_dir = Path(__file__).resolve().parent.parent
    workspace_root = Path.cwd()  # The directory where the user runs the command

    target_dirs = [".agents/workflows", ".gemini/workflows", ".cursor/rules"]

    workflows = {
        "curso-init": """---
description: auto inicializar un curso de Moodle capturando metadatos profundos
---
## Inicializar Curso (Discovery First)

1. **Descubrimiento (Opcional)**: Si no tienes el enlace, ve a `my/courses.php`.
2. **Navegar al Curso Seleccionado**: Ve a la página principal del curso.
3. **Extraer Datos Profundos**: Identifica PGA, Cronograma y Docente.
4. **Heurística de Teams (Seguridad)**: Valida que los enlaces del cronograma apunten directamente a `teams.microsoft.com`. Por seguridad, **NO navegues ni captures** links que sean redirecciones de Moodle o acortadores. Si no es directo, busca un link válido en la introducción o marca como `[PENDIENTE]`.
5. **Ejecutar Scaffolding**:
   Run `python {skill_dir}/scripts/scaffold_course.py "[Nombre]" "[URL]" ...`
6. **Poblar y Verificar Archivos**: Revisa `AGENTS.md` y `sitemap.md`. Es **CRÍTICO** que edites manualmente `AGENTS.md` para asegurarte de que ningún campo se quede con la plantilla `[PENDIENTE]`. Inserta la información faltante si el script no pudo hacerlo de forma automática.
""",
        "curso-sync": """---
description: sincronizar curso, generar sitemap y navegar mediante enlaces permanentes
---
## Sincronización y Bloqueo de Navegación

1. **Extracción de Barra Lateral (Mandatorio)**: Navega al curso, expande la barra lateral y recorre CADA unidad/sección para extraer su enlace directo. **IMPORTANTE**: Para enlaces de archivos (`pluginfile.php`), añade siempre `?forcedownload=1` para asegurar la descarga directa.
2. **Formación de Sitemap**: Actualiza `sitemap.md` con estos enlaces en la sección `## 🌐 Moodle Sections`.
3. **Descarga desde Sitemap**: Navega ÚNICAMENTE a través de los enlaces del sitemap para descargar materiales y organizarlos en `Unidad-X/materiales/`.
4. **Ejecutar Tooling**:
   Run `python {skill_dir}/scripts/sync_course.py "[Ruta del Curso]"`
5. **BLOQUEO DE RAZONAMIENTO**: Una vez el sitemap esté listo, tienes PROHIBIDO navegar ciegamente. Cualquier consulta posterior sobre este curso DEBE resolver su URL desde el `sitemap.md`.
""",
    }

    print(f"🚀 Deploying moodle-navigator workflows to: {workspace_root}")

    for r_dir in target_dirs:
        target_path = workspace_root / r_dir
        if (
            workspace_root / r_dir.split("/")[0]
        ).exists() or r_dir == ".agents/workflows":
            target_path.mkdir(parents=True, exist_ok=True)
            for name, content in workflows.items():
                ext = ".mdc" if "cursor" in r_dir else ".md"
                file_path = target_path / f"{name}{ext}"
                with open(file_path, "w", encoding="utf-8") as f:
                    # Inject absolute path to skill scripts
                    f.write(
                        content.replace(
                            "{skill_dir}", str(skill_dir).replace("\\", "/")
                        )
                    )
                print(f"  ✅ Deployed: {r_dir}/{name}{ext}")


if __name__ == "__main__":
    deploy()
