---
description: Inicializa uno o múltiples cursos académicos en paralelo, extrayendo metadatos de Moodle y validando la estructura final.
---

# 🏗️ Inicialización de Curso (Parallel & Verified)

Este flujo prepara el entorno de trabajo para tus cursos universitarios usando un enfoque multi-agente.

## 1. Descubrimiento y Paralelismo

Si necesitas inicializar **múltiples cursos**:

1. Identifica la lista de cursos en Moodle (`my/courses.php`).
2. **Orquestación**: Por cada curso, delega a un sub-agente especializado la tarea de "Inicialización Individual".
3. Usa la guía de `references/orchestration.md` para coordinar el paralelismo.

## 2. Inicialización Individual

Para cada curso:

1. **Scraping**: Extrae PGA, Cronograma y metadatos del docente usando el skill interno `.agent/skills/moodle-navigator`.
2. **Scaffolding**: Ejecuta el script de scaffolding:
   `python .agent/skills/moodle-navigator/scripts/scaffold_course.py "[Nombre]" "[URL]" ...`
3. **ClickUp**: Crea la lista correspondiente usando `.agent/skills/clickup-manager`.

## 3. Fase de Verificación (Crítica)

Tras completar el procesamiento de texto y la creación de archivos:

1. **Ejecutar Suite de Pruebas**:
   `python scripts/verify_workspace.py "[Ruta del Curso]"`
2. **Corrección Automática**: Si la suite detecta campos `[PENDIENTE]`, el agente DEBE volver a Moodle para re-intentar la captura de ese dato específico.
3. **Validación de Reglas**: Asegúrate de que `.agents/rules/moodle-folders.md` esté presente para guiar a futuros agentes en este workspace.

## 🧠 Instrucciones para el Agente

- La velocidad es clave: prioriza el paralelismo si hay 2+ cursos.
- La integridad es innegociable: no cierres el flujo hasta que `scripts/verify_workspace.py` devuelva un estado verde (✅ OK).
