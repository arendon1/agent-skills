---
description: auto inicializar un curso de Moodle capturando metadatos profundos
---
## Inicializar Curso (Discovery First)

1. **Descubrimiento (Opcional)**: Si no tienes el enlace, ve a `my/courses.php`.
   - Escanea el tablero "Vista general de curso".
   - Extrae Nombres, códigos (ej. `2601B04G1`) y URLs.
   - Pregunta al usuario: "¿Cuáles de estos cursos quieres inicializar?"
2. **Navegar al Curso Seleccionado**: Ve a la página principal del curso.
3. **Extraer Datos Profundos**: Identifica:
   - Nombre completo y Código de asignatura.
   - Año, Semestre y Bloque (extraer de la sección Introducción).
   - Docente y Email ("Conoce tu profesor").
   - Plan de Gestión Académica (Actividades, fechas, pesos).
   - Cronograma (Sesiones sincrónicas, enlaces de Teams).
   - **Mapa del sitio**: Extrae la lista de todas las secciones y sus enlaces permanentes.
4. **Ejecutar Scaffolding**:
   Run `python c:/Users/andres.rendon/Documents/Prompts/skills/moodle-navigator/scripts/scaffold_course.py "[Nombre]" "[URL]" --sitemap-data "[JSON_MAP]" ...`
5. **Poblar y Verificar Archivos**: Revisa `AGENTS.md` y `sitemap.md`. Es **CRÍTICO** que edites manualmente `AGENTS.md` para asegurarte de que ningún campo se quede con la plantilla `[PENDIENTE]`. Inserta la información faltante si el script no pudo hacerlo de forma automática.
