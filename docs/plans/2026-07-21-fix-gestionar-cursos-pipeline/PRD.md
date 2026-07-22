# PRD — fix(gestionar-cursos): local-plan mode + Moodle→ClickUp delta

## §G GOAL

`gestionar-cursos` produces local artifacts that the agent orchestrates with
`use-clickup`. No cross-imports. `cli_clickup.py` stops touching the API and
emits a declarative `sync_plan.json`. `cli_calificaciones.py` supports
100% "Pendiente" courses without crashing.

## §C CONSTRAINTS (from the user, hard)

C1. **No domain skill imports another.** `gestionar-cursos` MUST NOT import
    `use-clickup`. The agent (me / Hermes) orchestrates calls between
    skills, not the code.
C2. **Every Python script uses `uv` for dependency management** when it has
    any. `uv run python <script>` is the canonical invocation form.
C3. **Detection + status + comment.** For every activity with
    `calificacion != None` in the snapshot, plan: status → "calificado"
    (by name, NOT by id) + a comment with the grade in canonical format.
    Idempotent: re-running does not duplicate.
C4. **Flow direction: Moodle → Local → ClickUp, unidirectional.** ClickUp is
    terminal. Reclassifications / renames go as `to_update` of the same
    `task_id`. Deletions from Moodle go as `to_archive` (NOT `to_delete`).
C5. **Moodle = operational source of truth.** Local caches can be stale;
    the agent decides when to re-sync; the script does not assume a
    fresh cache.
C6. **Visual browser tests as many times as needed.** Validate against the
    real Moodle (gradebook) and the real ClickUp panel. Do not trust unit
    tests alone.
C7. **Local course must exist before planning ClickUp.** If it does not
    exist locally, `cli_clickup.py` aborts with a clear message — never
    auto-initializes anything.

## §O OUT OF SCOPE

- Broad refactor of the scripts (CLI with sub-commands, dataclasses,
  structured logging).
- Rewrite of `navegador_cdp.py`, `cli_init.py`, or existing orchestrators.
- Changes to the `use-clickup` skill (it works, it stays as the API).
- Auto-initialization of ClickUp courses from `cli_clickup.py` (that is
  the agent's decision).
- Linter / pre-commit hooks.

## §I INTERFACES (sketch)

### `_meta.orchestration_hint` and `_meta.idempotency_keys` (NEW)

Added to the schema for maximum agent autonomy (user rule 2026-07-21:
"minimum human interaction unless destructive action"):

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
      "unresolved with non-deterministic reason (see §B of sync-flow.md)"
    ]
  },
  "idempotency_keys": {
    "to_create": "list_id + name",
    "to_update": "task_id",
    "to_archive": "task_id"
  }
}
```

- `orchestration_hint.order` — the agent applies in that order.
  `to_create` first (so that later updates can reference new IDs if
  applicable).
- `tools_required` — orchestrator capabilities the plan assumes available.
  If any is missing, the agent aborts with a clear error (no partial
  apply).
- `pause_for_human` — the only case where the agent PAUSES before applying.
- `idempotency_keys` — the agent uses these fields to detect double-apply.
  Before applying any `to_update` or `to_archive`, verify that the most
  recent comment on the task does NOT start with `[calificaciones-auto]`.
  Before each `to_create`, verify that no task with the same
  `list_id + name` already exists.

### Behavior on `unresolved` (agent rule)

- **Auto-resolvable** (agent resolves and applies alone): `list_id`
  derivable from `curso_key` (list exists in `clickup.json`); `task_id`
  absent but `name` matches exactly against existing tasks in the list;
  Moodle rename that matches by canonical alias
  (`Prueba Inicial` → `PruebaInicial.md`).
- **Not auto-resolvable** (agent PAUSES and reports to the human):
  `curso_no_inicializado`, `folder_not_found`, `task_id_ambiguo`
  (multiple near matches), `list_id_null` with no matchable `curso_key`.
  The agent lists paused items in alphabetical order so the human can
  resolve them in a batch.

### New output: `sync_plan.json` (produced by `cli_clickup.py`)

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

**Schema contract:**

- `to_create` → POST `/list/{id}/task` with `name`, `tags`, `priority`,
  `due_date`.
- `to_update` → PUT `/task/{id}` with non-`null` fields in `diff` + POST
  `/task/{id}/comment` if `comment != null`.
- `to_archive` → PUT `/task/{id}` with `status: "cancelled"` (or the
  space's equivalent). NOT DELETE — preserves history.
- `unresolved` → the agent reports to the human; nothing is applied to
  ClickUp for these items.
- `diff.status.from` → if the actual ClickUp status does not match at
  apply time, the agent aborts that entry (race detected).

### CLI

```bash
uv run python scripts/cli_calificaciones.py <curso>             # exit 0, JSON + .md updated
uv run python scripts/cli_calificaciones.py <curso> --dry-run   # same, no writes
uv run python scripts/cli_clickup.py <periodo>                  # exit 0, sync_plan.json written
uv run python scripts/cli_clickup.py <periodo> --dry-run        # same, no writes
```

No script invokes `use-clickup`. Period.

### Env

- `CLICKUP_API_KEY` → used by the agent (via `use-clickup`), NOT by
  `gestionar-cursos` scripts.
- `OPENROUTER_API_KEY` → for the LLM, unchanged.

## §D DONE

D1. `cli_calificaciones.py` exits 0 on a course with all items
    "Pendiente".
D2. `snapshot.json` has a `calificacion` field for every activity
    (may be `null`).
D3. Activity `.md` files have a `## Calificación` section.
D4. `cli_clickup.py` exits 0 and produces a valid `sync_plan.json`.
D5. `sync_plan.json` has `to_create` / `to_update` / `to_archive` /
    `unresolved` classified correctly, without touching the ClickUp API.
D6. `pytest` exits 0 on the full skill suite.
D7. `skill-forge audit gestionar-cursos` exits 0 (SKILL.md <= 500 lines).
D8. Visual validation against Moodle (browser) and against the ClickUp
    panel (browser) confirms artifacts match reality.

## §V INVARIANTS (proposed, ARD/SPEC)

V1. `gestionar-cursos` MUST NOT `import` code from `use-clickup` or any
    other skill.
V2. `gestionar-cursos` MUST produce artifacts (`sync_plan.json`,
    `calificaciones.json`, `snapshot.json`) that the agent consumes with
    `use-clickup` or other tools.
V3. `_parse_porcentaje` MUST tolerate `" - %"`, `"100%"`, `"12,5 %"`,
    `"12.5 %"`, `"Sin calificar"`, `None`, `""`, `"-"`, `"—"` returning
    a float or `0.0` without raising.
V4. `cli_calificaciones.py:main` MUST persist
    (`_actualizar_md_actividad`, `_actualizar_snapshot`) BEFORE printing
    the summary; the summary is printed in ALL modes (even `--dry-run`).
V5. PUT /task to ClickUp MUST use `status` by name, NEVER `status_id`
    (lesson from 2026-2-B1).
V6. Re-running the pipeline MUST be idempotent: re-running MUST NOT
    duplicate status or comments in ClickUp.
V7. `sync_plan.json` MUST declare `_meta.schema_version` and be
    backward-stable within a major version.
V8. Skill tests MUST run with `uv run pytest` (not `python -m pytest`
    directly, not ad-hoc `pip install`).

## §Q OPEN QUESTIONS

- ? Does visual validation against ClickUp require a real
  `CLICKUP_API_KEY` in the test env, or is it done manually with
  `--dry-run` and a viewer? → Recommendation: manual with the browser,
  do not automate ClickUp E2E (cost + flakiness).
- ? Does `sync_plan.json` get overwritten or accumulated? → Recommend:
  overwrite with a timestamp in `_meta.generated_at`; the agent decides
  when to apply.
- ? What happens with items in ClickUp that do NOT exist in Moodle
  (orphans)? → Recommend: do not plan them (the delta is
  Moodle-centric). Document in SKILL.md as an expected case after
  manual user errors.

## §B BUGS (what this fix resolves)

| id  | date       | cause                                                                 | fix                  |
|-----|------------|-----------------------------------------------------------------------|----------------------|
| B1  | 2026-07-21 | `float(it["aporte_curso"].replace(...).strip() or 0)` crashes on `"-"` | `_parse_porcentaje` with explicit sentinels |
| B2  | 2026-07-21 | `_imprimir_resumen` before `_actualizar_md_actividad` / `_actualizar_snapshot` | reorder main() + try/except |
| B3  | 2026-07-21 | `cli_clickup.py` calls `get_client()` without import (NameError)      | deprecated: the script now produces `sync_plan.json`; does not use `use-clickup` |
| B4  | 2026-07-21 | `cli_clickup.py:127,132,388,421` uses 4 free functions of `use-clickup` not imported | same as B3: the script no longer needs them |
| B5  | 2026-07-21 | SKILL.md exceeds 500 lines (586)                                      | refactor: move sections to `references/` |
| B6  | 2026-07-21 | `pyproject.toml` already has a `[dependency-groups]` block; duplicating it causes `TOMLDecodeError` | add `pytest` to the existing array |
| B7  | 2026-07-21 | proposed tests don't mock Rich's `console`, fail in CI without a TTY  | mock `console` with `StringIO` in conftest |

## §R REFS

- `AGENTS.md` at repo root — repo constitution
  (§3 layers, §9 agnosticism, §11 right-size, §15 size).
- `use-clickup/scripts/client.py` — API consumed by the agent (not by
  the skill).
- `references/sync-flow.md` (NEW) — agent/skill contract + end-to-end
  flow.
- `references/folder-structure.md` (NEW) — extracted from SKILL.md.
- `references/agents-md-template.md` (NEW) — extracted from SKILL.md.
