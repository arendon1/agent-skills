---
description: sincronizar curso, generar sitemap y convertir materiales a Markdown
---
## Sincronizar Curso

1. **Identificar Ruta**: Localiza la carpeta del curso en el workspace.
2. **Ejecutar Sync**:
   Run `uv run c:/Users/andres.rendon/Documents/Prompts/skills/moodle-navigator/scripts/sync_course.py "[Ruta del Curso]"`
3. **Revisar Sitemap**: Abre el archivo `sitemap.md` generado para verificar que todas las secciones y enlaces estén presentes.
4. **Validar Materiales**: Verifica que los archivos PDF/DOCX se hayan convertido a `.md` para facilitar la lectura por parte de los agentes.
