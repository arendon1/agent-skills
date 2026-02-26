---
description: auto inicializar un curso de Moodle capturando metadatos profundos
---
## Inicializar Curso (Discovery First)

1. **Descubrimiento (Opcional)**: Si no tienes el enlace, ve a `my/courses.php`.
2. **Navegar al Curso Seleccionado**: Ve a la página principal del curso.
3. **Extraer Datos Profundos**: Identifica PGA, Cronograma y Docente.
4. **Heurística de Teams (Seguridad)**: Valida que los enlaces del cronograma apunten directamente a `teams.microsoft.com`. Por seguridad, **NO navegues ni captures** links que sean redirecciones de Moodle o acortadores. Si no es directo, busca un link válido en la introducción o marca como `[PENDIENTE]`.
5. **Ejecutar Scaffolding**:
   Run `python C:/Users/andres.rendon/Documents/Prompts/skills/moodle-navigator/scripts/scaffold_course.py "[Nombre]" "[URL]" ...`
6. **Poblar y Verificar Archivos**: Revisa `AGENTS.md` y `sitemap.md`. Es **CRÍTICO** que edites manualmente `AGENTS.md` para asegurarte de que ningún campo se quede con la plantilla `[PENDIENTE]`. Inserta la información faltante si el script no pudo hacerlo de forma automática.
