---
description: sincronizar curso, generar sitemap y navegar mediante enlaces permanentes
---
## Sincronización y Bloqueo de Navegación

1. **Extracción de Barra Lateral (Mandatorio)**: Navega al curso, expande la barra lateral y recorre CADA unidad/sección para extraer su enlace directo.
2. **Formación de Sitemap**: Actualiza `sitemap.md` con estos enlaces en la sección `## 🌐 Moodle Sections`.
3. **Descarga desde Sitemap**: Navega ÚNICAMENTE a través de los enlaces del sitemap para descargar materiales y organizarlos en `Unidad-X/materiales/`.
4. **Ejecutar Tooling**:
   Run `python C:/Users/andres.rendon/Documents/Prompts/skills/moodle-navigator/scripts/sync_course.py "[Ruta del Curso]"`
5. **BLOQUEO DE RAZONAMIENTO**: Una vez el sitemap esté listo, tienes PROHIBIDO navegar ciegamente. Cualquier consulta posterior sobre este curso DEBE resolver su URL desde el `sitemap.md`.
