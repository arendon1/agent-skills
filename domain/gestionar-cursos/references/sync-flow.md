# sync-flow — playbook ejecutable agente ↔ ClickUp

Documento **ejecutable**, no descriptivo. El agente lo lee una vez
y aplica el `sync_plan.json` siguiendo los pasos numerados abajo.
NO improvisa. El modo de operacion es autonomo por defecto
(L11): solo pausa para input humano en los casos de §B.

## §A — Aplicacion autonoma (caso normal)

Pasos numerados que el agente ejecuta en orden:

1. Leer `sync_plan.json`.
2. Verificar `_meta.schema_version` (abortar si != 1).
3. Verificar capabilities del orquestador contra
   `_meta.orchestration_hint.tools_required`. Si falta alguna,
   abortar con error claro (no aplicar parcialmente).
4. Para cada item en `_meta.orchestration_hint.order`:

   a. `to_create`:
      - Pre-check: `GET /list/{list_id}/task?name=<name>` para
        confirmar que no existe.
      - Si existe con mismo nombre: skip (idempotente).
      - Si no existe: `POST /list/{list_id}/task` con
        `name + tags + priority + due_date_ms`.

   b. `to_update`:
      - Pre-check: `GET /task/{task_id}/comment` para leer el ultimo
        comentario.
      - Si el ultimo comentario empieza con `[calificaciones-auto]`:
        skip (idempotente).
      - Verificar `diff.status.from` contra `GET /task/{task_id}.status`
        (deteccion de carrera).
      - Si hay divergencia: log warning y abortar ESA entrada
        (no todo el plan).
      - Si OK: `PUT /task/{task_id}` con los campos no-null del
        `diff`.
      - Si `diff.comment != null`: `POST /task/{task_id}/comment`
        con `comment.text`.

   c. `to_archive`:
      - Pre-check: `GET /task/{task_id}.status`.
      - Si status ya es `"cancelled"`: skip (idempotente).
      - `PUT /task/{task_id}` con `status: "cancelled"`.

5. Log resumen: `aplicadas / skipped / abortadas / paused`.

El agente registra el resultado de cada entrada en
`_meta.applied_results` (campo nuevo en el plan post-aplicacion)
para auditoria.

## §B — Pausa para input humano (unico caso)

Solo cuando `unresolved` contiene items con razon **no determinista**:

- `curso_no_inicializado` — el humano debe correr `cli_init.py` primero.
- `folder_not_found` — el humano debe crear el folder en ClickUp
  manualmente.
- `task_id_ambiguo` — multiples tareas aproximadas; el humano elige
  una o ignora.
- `list_id_null` — el curso existe en Moodle pero no en `clickup.json`;
  el humano decide si correr `cli_init.py` para inicializarlo.

El agente lista los items pausados en orden alfabetico y reporta el
batch completo. NO pausa uno por uno.

Todo lo demas se ejecuta sin pausa: pre-checks idempotentes, aborts
de carrera, deduplicacion por nombre/tag, y todas las operaciones
listadas en §A.

## §C — Acciones destructivas PROHIBIDAS

Lista explicita que el agente **NUNCA** debe ejecutar:

- `DELETE /task/{id}` — el plan solo planifica `to_archive`, nunca
  `to_delete`. Preservar historial es sagrado (L10).
- Reorganizacion del workspace ClickUp (mover tasks entre lists,
  cambiar jerarquia de folders, renombrar espacios).
- Edicion de statuses personalizados del space Universidad.
- Cualquier operacion que afecte tareas que **NO** estan en el
  `sync_plan.json` (ej. tareas manuales del humano que no vinieron
  de Moodle).

Si el agente detecta que una operacion requerida cae en §C, aborta
ESA operacion con error explicito y continua con las demas. NO
consulta al humano: la prohibicion ya esta en este playbook.

## §D — Quirk conocido: `status_id` vs `status` name

Leccion preservada del commit `6d7fb79` / caso `2026-2-B1`:
`PUT /task/{id}` rechaza `status_id` (ID numerico) con **400 Bad
Request**. SIEMPRE enviar `status` como nombre del status:

```json
{ "status": "calificado" }
{ "status": "pendiente" }
{ "status": "cancelled" }
```

El `client.py` de `use-clickup` no documenta esto explicitamente;
el bug se manifiesta como "el status se queda en pendiente aunque la
respuesta sea 200" o como 400 directo. Ver `references/fechas-fuente-de-verdad.md`
y LESSONS.md L4 / L11.

## §E — Tabla de idempotencia (para audit)

| Operacion    | Key               | Pre-check                                |
|--------------|-------------------|------------------------------------------|
| `to_create`  | `list_id + name`  | `GET /list/{list_id}/task?name=X` vacio? |
| `to_update`  | `task_id`         | `GET /task/{id}/comment` sin tag auto    |
| `to_archive` | `task_id`         | `GET /task/{id}.status != "cancelled"?`  |
| `unresolved` | n/a               | siempre requiere intervencion            |

Si la pre-check falla (ya aplicado), skip silencioso. Si la
pre-check pasa pero la operacion PUT/POST falla, abort ESA entrada
(no todo el plan) y registra en `_meta.applied_results`.
