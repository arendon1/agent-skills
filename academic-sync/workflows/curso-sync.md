---
description: Sincroniza las actividades de Moodle con ClickUp usando una heurística inteligente.
---

# 🔄 Sincronización de actividades (Moodle to ClickUp)

Este flujo sincroniza las fechas y ponderaciones de las tareas.

## 1. Contexto Predeterminado

- Leer el archivo `AGENTS.md` local para obtener el `COURSE_ID` y el `CLICKUP_LIST_ID`.
- Si no existen, informar que debe ejecutarse `curso-init` primero.

## 2. Extracción de Datos (Moodle)

- Navegar a la tabla **`DO-FR-66 Plan de Gestión Académica`** en la sección de Introducción.
- Extraer: Actividad, %, Fecha Inicio, Fecha Cierre.
- **Formato**: Fechas en DD/MM/YYYY hh:mm.

## 3. Heurística de Sincronización Inteligente

Antes de crear, el agente debe:

1. Listar tareas de ClickUp: `python scripts/clickup_client.py list-tasks --format brief`.
2. Comparar cada actividad de Moodle:
   - **Update**: Si el nombre coincide (exacta o semánticamente), actualizar fechas y ponderación (%) en la descripción o campos personalizados.
   - **Create**: Solo si la actividad no existe en ClickUp.
3. **Optimización**: No crear duplicados de tareas de tipo "Encuentro Sincrónico" si ya están mapeadas.

## 4. Ejecución

- Convertir fechas a Epoch Milliseconds (Ajuste UTC-5 Colombia).
- Usar `clickup-manager` para ejecutar las mutaciones.
- Confirmar al usuario el resumen de cambios (X creadas, Y actualizadas).

## 🧠 Instrucciones para el Agente

- Mantén siempre el idioma en **Español**.
- Si encuentras discrepancias entre lo que dice el calendario de Moodle y la tabla `DO-FR-66`, **prioriza la tabla `DO-FR-66`** como fuente de verdad.
