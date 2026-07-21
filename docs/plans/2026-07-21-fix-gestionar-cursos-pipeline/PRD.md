# PRD — fix(gestionar-cursos): modo plan-local + delta Moodle→ClickUp

## §G GOAL

`gestionar-cursos` produce artefactos locales que el agente orquesta con `use-clickup`.
Sin imports cruzados. `cli_clickup.py` deja de tocar la API y emite `sync_plan.json`
declarativo. `cli_calificaciones.py` soporta cursos 100% Pendiente sin crashear.

## §C CONSTRAINTS (del usuario, hard)

C1. **Ningún skill de dominio importa otro.** `gestionar-cursos` NO importa `use-clickup`.
    El agente (yo/Hermes) orquesta las llamadas entre skills, no el código.

C2. **Todo script Python usa `uv` para gestionar dependencias** si las requiere.
    `uv run python <script>` es la forma canónica de invocar.

C3. **Detección + status + comentario.** Para cada actividad con `calificacion != None`
    en el snapshot, planificar: status → "calificado" (por nombre, NO por id) + comentario
    con la nota en formato canónico. Idempotente: re-correr no duplica.

C4. **Direccion de flujo: Moodle → Local → ClickUp, unidireccional.** ClickUp es terminal.
    Reclasificaciones / renombres van como `to_update` del mismo `task_id`. Eliminaciones
    de Moodle van como `to_archive` (NO `to_delete`).

C5. **Moodle = fuente de verdad operativa.** Las caches locales pueden estar stale;
    el agente decide cuándo re-sincronizar; el script no asume cache fresca.

C6. **Pruebas visuales con browser cuantas veces haga falta.** Validar contra Moodle
    real (gradebook) y contra panel real de ClickUp. No fiarse de tests unitarios solos.

C7. **Course local debe existir antes de planificar ClickUp.** Si no existe local,
    `cli_clickup.py` aborta con mensaje claro — no auto-inicializa nada.

## §O OUT OF SCOPE

- Refactor amplio de los scripts (CLI con sub-comandos, dataclasses, logging estructurado).
- Reescritura de `navegador_cdp.py`, `cli_init.py` u orquestadores existentes.
- Cambios al skill `use-clickup` (funciona, queda como API).
- Auto-inicialización de cursos en ClickUp desde `cli_clickup.py` (decisión del agente).
- Linter / pre-commit hooks.

## §I INTERFACES (sketch)

### `_meta.orchestration_hint` y `_meta.idempotency_keys` (NUEVO)

Anadidos al schema para maxima autonomia del agente (regla del usuario 2026-07-21:
"minima interaccion humana salvo accion destructiva"):

```json
"_meta": {
  "periodo": "2026-2-B1",
  "generated_at": "2026-07-21T15:30:00-05:00",
  "source": "moodle",
  "schema_version": 1,
  "orchestration_hint": {
    "order": ["to_create", "to_update", "to_archive"],
    "tools_required": [
      "use-clickup:create_task",
      "use-clickup:update_task",
      "use-clickup:post_comment"
    ],
    "pause_for_human": [
      "unresolved con razon no determinista (ver §B de sync-flow.md)"
    ]
  },
  "idempotency_keys": {
    "to_create": "list_id + name",
    "to_update": "task_id",
    "to_archive": "task_id"
  }
}
```

- `orchestration_hint.order` — el agente aplica en ese orden. `to_create` primero
  (para que las actualizaciones posteriores puedan referenciar IDs nuevos si aplica).
- `tools_required` — capabilities del orquestador que el plan asume disponibles.
  Si alguna falta, el agente aborta con error claro (no aplica parcialmente).
- `pause_for_human` — el unico caso donde el agente PAUSA antes de aplicar.
- `idempotency_keys` — el agente usa estos campos para detectar doble-aplicacion.
  Antes de aplicar cada `to_update` o `to_archive`, verifica que el comentario
  mas reciente de la tarea NO empiece con `[calificaciones-auto]`. Antes de cada
  `to_create`, verifica que no exista ya una tarea con `list_id + name` identico.

### Comportamiento ante `unresolved` (regla del agente)

- **Auto-resoluble** (agente resuelve y aplica solo): `list_id` derivable del
  `curso_key` (list existe en `clickup.json`); `task_id` ausente pero `name`
  matchea exactamente contra tareas existentes en la list; renombre de Moodle
  que matchea por alias canonico (`Prueba Inicial` → `PruebaInicial.md`).
- **No auto-resoluble** (agente PAUSA y reporta al humano): `curso_no_inicializado`,
  `folder_not_found`, `task_id_ambiguo` (multiples matches近似), `list_id_null`
  sin curso_key matcheable. El agente lista los items pausados en orden
  alfabetico para que el humano resuelva en batch.

### Salida nueva: `sync_plan.json` (producido por `cli_clickup.py`)

```json
{
  "_meta": {
    "periodo": "2026-2-B1",
    "generated_at": "2026-07-21T15:30:00-05:00",
    "source": "moodle",
    "schema_version": 1
  },
  "to_create": [
    {
      "task_id": null,
      "list_id": "9013234567",
      "name": "Primer Parcial",
      "tags": ["parcial", "quiz"],
      "priority": "urgent",
      "due_date_ms": 1738368000000,
      "due_date_source": "snapshot"
    }
  ],
  "to_update": [
    {
      "task_id": "86abc123",
      "list_id": "9013234567",
      "diff": {
        "status": {"from": "pendiente", "to": "calificado"},
        "name": null,
        "due_date_ms": null
      },
      "comment": {
        "text": "[calificaciones-auto] Calificación sincronizada desde Moodle\n\n- **Curso:** LPA 1\n- **Actividad:** Primer Parcial (25%)\n- **Nota:** 4,80 / 5,00 (96,00%)\n- **Aporte al curso:** 24,00%\n- **Capturado:** 2026-07-17T01:21:11",
        "tag": "[calificaciones-auto]"
      }
    }
  ],
  "to_archive": [
    {
      "task_id": "86abc987",
      "list_id": "9013234567",
      "reason": "removed_from_moodle"
    }
  ],
  "unresolved": [
    {
      "item": "Actividad X sin task_id",
      "reason": "clickup.list_id es null o no existe"
    }
  ]
}
```

**Contrato del schema:**

- `to_create` → POST `/list/{id}/task` con `name`, `tags`, `priority`, `due_date`.
- `to_update` → PUT `/task/{id}` con campos en `diff` que NO son `null` + POST `/task/{id}/comment` si `comment != null`.
- `to_archive` → PUT `/task/{id}` con `status: "cancelled"` (o el equivalente del space). NO DELETE — preserva historial.
- `unresolved` → el agente reporta al humano; nada se aplica a ClickUp para estos items.
- `diff.status.from` → si el estado real en ClickUp no coincide al momento de aplicar, el agente aborta esa entrada (carrera detectada).

### CLI

```bash
uv run python scripts/cli_calificaciones.py <curso>             # exit 0, JSON + .md actualizados
uv run python scripts/cli_calificaciones.py <curso> --dry-run   # mismo, sin escribir
uv run python scripts/cli_clickup.py <periodo>                  # exit 0, sync_plan.json escrito
uv run python scripts/cli_clickup.py <periodo> --dry-run        # mismo, sin escribir
```

Ningun script invoca `use-clickup`. Punto.

### Env

- `CLICKUP_API_KEY` → la usa el agente (vía `use-clickup`), NO los scripts de `gestionar-cursos`.
- `OPENROUTER_API_KEY` → para LLM, sin cambios.

## §D DONE

D1. `cli_calificaciones.py` corre exit 0 sobre curso con todos los items "Pendiente".
D2. `snapshot.json` tiene campo `calificacion` por cada actividad (puede ser `null`).
D3. Los archivos `.md` de actividades tienen sección `## Calificación`.
D4. `cli_clickup.py` corre exit 0 y produce `sync_plan.json` válido.
D5. `sync_plan.json` tiene `to_create` / `to_update` / `to_archive` / `unresolved`
    clasificados correctamente, sin tocar la API de ClickUp.
D6. `pytest` exit 0 sobre toda la suite del skill.
D7. `skill-forge audit gestionar-cursos` exit 0 (SKILL.md <= 500 líneas).
D8. Validación visual contra Moodle (browser) y contra panel de ClickUp (browser)
    confirma que los artefactos coinciden con la realidad.

## §V INVARIANTS (propuesto, ARD/SPEC)

V1. `gestionar-cursos` MUST NOT `import` código de `use-clickup` ni de ningún otro skill.
V2. `gestionar-cursos` MUST producir artefactos (`sync_plan.json`, `calificaciones.json`,
    `snapshot.json`) que el agente consume con `use-clickup` u otras herramientas.
V3. `_parse_porcentaje` MUST tolerar `" - %"`, `"100%"`, `"12,5 %"`, `"12.5 %"`,
    `"Sin calificar"`, `None`, `""`, `"-"`, `"—"` retornando float o 0.0 sin excepcion.
V4. `cli_calificaciones.py:main` MUST persistir (`_actualizar_md_actividad`,
    `_actualizar_snapshot`) ANTES de imprimir resumen; resumen se imprime en
    TODOS los modos (incluso `--dry-run`).
V5. PUT /task a ClickUp MUST usar `status` por nombre, NUNCA `status_id` (lección 2026-2-B1).
V6. Re-ejecucion del pipeline MUST ser idempotente: re-correr NO duplica status
    ni comentarios en ClickUp.
V7. `sync_plan.json` MUST declarar `_meta.schema_version` y ser estable hacia atras
    dentro de la major version.
V8. Tests del skill MUST correr con `uv run pytest` (no `python -m pytest` directo,
    no `pip install` ad-hoc).

## §Q OPEN QUESTIONS

- ? ¿La validación visual contra ClickUp requiere `CLICKUP_API_KEY` real en el
  entorno de tests, o se hace manual con `--dry-run` y un viewer? → Recomendado:
  manual con el browser, no automatizar E2E de ClickUp (costo + flakiness).
- ? ¿`sync_plan.json` se sobre-escribe o se acumula? → Recomendado: sobre-escribe
  con timestamp en `_meta.generated_at`; el agente decide cuándo aplicar.
- ? ¿Qué pasa con items en ClickUp que NO existen en Moodle (huérfanos)? →
  Recomendado: no se planifican (el delta es Moodle-centric). Se documenta en
  SKILL.md como caso esperado tras errores manuales del usuario.

## §B BUGS (los que arregla este fix)

| id  | date       | cause                                                                 | fix                  |
|-----|------------|-----------------------------------------------------------------------|----------------------|
| B1  | 2026-07-21 | `float(it["aporte_curso"].replace(...).strip() or 0)` crashea con `"-"` | `_parse_porcentaje` con centinelas explicitos |
| B2  | 2026-07-21 | `_imprimir_resumen` antes de `_actualizar_md_actividad`/`_actualizar_snapshot` | reordenar main() + try/except |
| B3  | 2026-07-21 | `cli_clickup.py` llama `get_client()` sin import (NameError)         | deprecado: el script ahora produce `sync_plan.json`; no usa `use-clickup` |
| B4  | 2026-07-21 | `cli_clickup.py:127,132,388,421` usa 4 funciones libres de `use-clickup` no importadas | idem B3: el script ya no las necesita |
| B5  | 2026-07-21 | SKILL.md excede 500 líneas (586)                                      | refactor: mover secciones a `references/` |
| B6  | 2026-07-21 | `pyproject.toml` ya tiene bloque `[dependency-groups]`; duplicarlo causa `TOMLDecodeError` | añadir `pytest` al array existente |
| B7  | 2026-07-21 | tests propuestos no mockean `console` de Rich, fallan en CI sin TTY    | mockear `console` con `StringIO` en conftest |

## §R REFS

- `AGENTS.md` raiz — constitucion del repo (§3 layers, §9 agnosticismo, §11 right-size, §15 size).
- `use-clickup/scripts/client.py` — API consumida por el agente (no por el skill).
- `references/sync-flow.md` (NUEVO) — contrato agente/skill + flujo end-to-end.
- `references/folder-structure.md` (NUEVO) — extraido de SKILL.md.
- `references/agents-md-template.md` (NUEVO) — extraido de SKILL.md.
