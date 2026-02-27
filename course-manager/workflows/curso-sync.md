---
description: Sincroniza actividades académicas (PGA) de Moodle a ClickUp para gestión personal de fechas y tareas.
---

# 🔄 Sincronización de Actividades (Personal Sync)

Este flujo mantiene tus tareas de ClickUp alineadas con el plan académico oficial de Moodle.

## 1. Preparación de Contexto

1. **Lectura de AGENTS.md**: El agente debe leer el archivo `AGENTS.md` local para obtener el `LIST_ID` de ClickUp y la `COURSE_URL` de Moodle.
2. **Validación Previa**: Ejecutar `python scripts/verify_workspace.py .` para confirmar que el contexto local es válido antes de sincronizar.

## 2. Extracción y Mapeo

1. **Moodle**: Usar `.agent/skills/moodle-navigator` para extraer la tabla del Plan de Gestión Académica (DO-FR-66).
2. **Mapeo de Campos**:
   - Actividad -> Task Name.
   - Fecha Fin -> Due Date.
   - Peso -> Task Description/Tag.
3. **ClickUp**: Usar `.agent/skills/clickup-manager` para crear o actualizar las tareas en la lista correspondiente.

## 3. Heurística Anti-Duplicado

- El agente **DEBE** verificar si ya existen tareas con el mismo nombre y fecha en ClickUp antes de crear nuevas.
- Si hay cambios en las fechas en Moodle, el agente debe **Actualizar** la tarea existente y notificar al usuario sobre el cambio de cronograma.

## 🧠 Instrucciones para el Agente

- Prioriza la precisión de las fechas. Un error en la fecha de entrega es un fallo crítico del sistema.
- Si el `LIST_ID` no está en `AGENTS.md`, intenta localizar la lista por el nombre del curso en ClickUp usando `clickup-manager`.
