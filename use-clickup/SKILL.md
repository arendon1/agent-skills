---
name: use-clickup
description: >-
  Gestión de tareas y listas en ClickUp via API oficial.
  Úsalo para crear tareas, actualizar fechas, buscar actividades,
  y organizar listas de cursos.
metadata:
  version: "1.0.0"
  language: es-CO
  risk_tier: MEDIUM
---

# /use-clickup

Skill para gestión completa de ClickUp. Solo workflows esenciales,
con documentación interna completa en `references/` para capacidades avanzadas.

## Autenticación

La API key se busca en orden:
1. Archivo `.env` en workspace actual (variable `CLICKUP_API_KEY`)
2. Variable de entorno `CLICKUP_API_KEY`
3. Error claro con instrucciones si no se encuentra

## Workflows

### /use-clickup crear-tarea

**Uso:** `crear-tarea <lista_id> <nombre> [--descripcion] [--due_date] [--tags] [--prioridad]`

**Ejemplo:**
```
/use-clickup crear-tarea abc123 "Prueba Inicial" \
  --descripcion "## Instrucciones\nLeer capítulo 1" \
  --due_date 2026-02-01 \
  --tags evaluable,parcial \
  --prioridad normal
```

**Tags válidos:** evaluable, no-evaluable, parcial, cuestionario, foro, taller, examen, actividad, material, recurso

**Prioridades:** urgent, high, normal, low

---

### /use-clickup actualizar-tarea

**Uso:** `actualizar-tarea <task_id> [--nombre] [--descripcion] [--due_date] [--prioridad] [--tags]`

**Ejemplo:**
```
/use-clickup actualizar-tarea def456 \
  --due_date 2026-02-15 \
  --prioridad high
```

**Nota:** Custom fields no se pueden actualizar via este workflow.

---

### /use-clickup buscar-tarea

**Uso:** `buscar-tarea [--nombre] [--tag] [--lista_id]`

**Ejemplo:**
```
/use-clickup buscar-tarea --nombre "Parcial" --tag evaluable
```

---

### /use-clickup crear-lista

**Uso:** `crear-lista <folder_id> <nombre>`

**Ejemplo:**
```
/use-clickup crear-lista folder123 "BASES DE DATOS 2 - 2601B04G1"
```

---

### /use-clickup ver-listas

**Uso:** `ver-listas [--folder_id] [--space_id]`

**Ejemplo:**
```
/use-clickup ver-listas --folder_id folder123
```

---

## Manejo de Errores

| Código | Significado | retry? | Acción |
|--------|-------------|--------|--------|
| 200 | Éxito | - | Continuar |
| 400 | Bad request | No | Corregir input |
| 401 | Auth fallida | No | Verificar API key |
| 403 | Sin permisos | No | Verificar acceso |
| 404 | No encontrado | No | Verificar ID |
| 409 | Conflicto | No | Resolver duplicado |
| 429 | Rate limit | Sí | Backoff 1s, 2s, 4s |
| 500 | Error servidor | Sí | Reintentar 3x |

## Referencias Internas

La documentación completa de la API está en `references/`:
- `api-tasks.md` — Todos los endpoints de tasks
- `api-lists.md` — CRUD de listas
- `api-folders.md` — CRUD de folders
- `api-spaces.md` — CRUD de spaces
- `api-comments.md` — Comments
- `api-checklists.md` — Checklists
- `api-tags.md` — Gestión de tags
- `api-custom-fields.md` — Custom fields
- `formato-fechas.md` — Conversión ISO ↔ milisegundos
- `manejo-errores.md` — Códigos y estrategias de retry