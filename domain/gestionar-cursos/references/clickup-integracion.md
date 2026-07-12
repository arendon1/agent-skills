# ClickUp — referencia de integración

Detalles de la integración entre `gestionar-cursos` y `use-clickup`.
SKILL.md resume el flujo; aquí están los detalles de estructura,
tags, y los comandos de sincronización.

## `clickup.json`

Un archivo por período académico en la raíz del workspace. Indexa
space, folder, listas y tareas de todas las materias de ese período.
`init` lo crea o lo extiende con la entrada del nuevo curso.

## Estructura en ClickUp

```
Universidad (space, id fijo: 901311224662)
└── 2026-2-B1 (folder, uno por período-bloque)
    ├── HUMANIDADES II - 2601B04G1 (list, una por curso)
    └── BASES DE DATOS 2 - 2601B05G2 (list)
```

## Flujo tras `init`

1. Al terminar `init`, avisar al usuario: "¿Sincronizar con ClickUp?"
2. Si confirma → ejecutar `cli_clickup.py`:

```bash
cd gestionar-cursos/scripts
uv run python cli_clickup.py "C:/Users/.../Universidad/2026-2-B1"
```

3. Se puede previsualizar con `--dry-run` antes de confirmar.

`cli_clickup.py`:
1. Resuelve `folder.id` y `list.id` en el espacio "Universidad" (crea
   si no existen).
2. Crea tareas en ClickUp para cada actividad del PGA no sincronizada.
3. Actualiza `AGENTS.md` con `CLICKUP_LIST_ID` y `clickup.json` con
   los IDs resueltos.

## Flujo tras `estado`

1. Ejecutar `cli_estado.py` → detectar cambios de fecha y nuevas
   actividades.
2. Preguntar: "¿Actualizar tareas en ClickUp con estos cambios?"
3. Si confirma → `cli_clickup.py` actualiza fechas modificadas y crea
   tareas nuevas.

## Tags del Skill

El skill define el conjunto canónico. `use-clickup` solo transporta
los tags a la API; no define cuáles son válidos.

### Tags de tipo de actividad (determinan prioridad)

| Tag | Criterio | Prioridad |
|-----|----------|-----------|
| `parcial` | Ponderación ≥15% o nombre contiene "parcial" | `urgente` |
| `quiz` | Ponderación <15% o "cuestionario"/"prueba" | `normal` |
| `actividad` | Assignment, seguimiento, tarea, trabajo | `alta` |
| `foro` | Foro de discusión | `normal` |

### Tags de evaluación

| Tag | Significado |
|-----|------------|
| `evaluable` | Tiene nota en el PGA |
| `no-evaluable` | Formativo, sin calificación |

### Tags de soporte (combinables)

| Tag | Cuándo |
|-----|--------|
| `grupal` | Trabajo en equipo |
| `entregable` | Requiere subir archivo o enlace |
| `lectura` | Leer material obligatorio |
| `repaso` | Estudiar para parcial/quiz |
| `documento` | Redactar informe, ensayo |
| `investigar` | Buscar fuentes, datos |
| `practica` | Ejercicios, código, laboratorio |
| `exposicion` | Preparar presentación |
| `participacion` | Requiere intervenir en foro/clase |
