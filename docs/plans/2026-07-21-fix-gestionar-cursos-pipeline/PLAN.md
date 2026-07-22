# PLAN — fix(gestionar-cursos): local-plan mode + Moodle→ClickUp delta

## §T TASKS

```
id|status|task|cites
T0|[ ]|isolated commit of sync_calificaciones_clickup.py (change from 6d7fb79)|G,C5
T1|[ ]|_parse_porcentaje in scripts/_parsing.py, tolerant of 10+ formats|V3,B1
T2|[ ]|fix main() in cli_calificaciones.py: persist before printing, dry-run prints|V4,B2
T3|[ ]|cli_clickup.py rewritten as local-plan: produces sync_plan.json, does not touch API|V1,B3,B4
T4|[ ]|tests/ with conftest.py that mocks Rich's console and pre-populates sys.path|V8,B7
T5|[ ]|test_parsing.py: 12+ cases for _parse_porcentaje|V3
T6|[ ]|test_cli_calificaciones.py: B1 (all Pendiente) + B2 (persistence order)|V3,V4
T7|[ ]|test_cli_clickup_plan.py: produces valid sync_plan.json without touching the API|V1,V7
T8|[ ]|pyproject.toml: add pytest to the existing dev array|V8,B6
T9|[ ]|SKILL.md refactor: move sections to references/, stays <= 450 lines|V5 §15
T10|[ ]|references/sync-flow.md NEW: agent/skill contract + delta + idempotency|C1,C3,C4
T11|[ ]|references/folder-structure.md NEW: extracted from SKILL.md|T9
T12|[ ]|references/agents-md-template.md NEW: extracted from SKILL.md|T9
T13|[ ]|CONTEXT.md at root: add terms sync_plan, delta, agent-orchestrator, flow-direction|C1
T14|[ ]|LESSONS.md: add L8 stale caches, L9 no-import rule, L10 clickup terminal|C5,C1,C4
T15|[ ]|visual browser validation: Moodle gradebook + ClickUp panel|C6
T16|[ ]|skill-forge audit gestionar-cursos: exit 0|V5
T17|[ ]|pytest exit 0 on the full suite|V8
T18|[ ]|conventional commit with body explaining the model change (a)|G
```

## §I INTERFACES (sketch, ratified in PRD)

### `sync_plan.json` (NEW, produced by `cli_clickup.py`)

See PRD §I for the full schema. Key design decisions:

- `to_update.diff.status.from` → if it does not match at apply time, the
  agent aborts that entry.
- `comment` separated from `diff` → separate POST, avoids wiping the
  comment.
- `_meta.schema_version` → for forward compatibility.
- `unresolved` → items the plan cannot resolve; the agent reports them
  to the human.

### `_parse_porcentaje` (NEW helper, in `scripts/_parsing.py`)

```python
def _parse_porcentaje(valor) -> float:
    """Parse a percentage value from a Moodle gradebook.
    Tolerant of None, "", "-", "—", "N/A", "Sin calificar", "100%",
    " - %", "12,5 %", "12.5 %", " 12,50 % ". Returns a float or 0.0 if
    not parseable.
    """
    if valor is None:
        return 0.0
    s = str(valor).strip()
    if not s or s in ("-", "—", "N/A", "Sin calificar"):
        return 0.0
    try:
        # Strip % and normalize decimal comma
        cleaned = s.replace("%", "").replace(",", ".").strip()
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0
```

Cases covered (at least 12): `None`, `""`, `"-"`, `"—"`, `"N/A"`,
`"Sin calificar"`, `"0,00 %"`, `"12,50 %"`, `"100,00 %"`, `"100%"`,
`" - %"`, `"12.5 %"`.

## §N IMPLEMENTATION NOTES

### T0 — Isolated commit of `sync_calificaciones_clickup.py`

```bash
git status  # confirm modified
git diff domain/gestionar-cursos/scripts/sync_calificaciones_clickup.py
git add domain/gestionar-cursos/scripts/sync_calificaciones_clickup.py
git commit -m "chore(gestionar-cursos): preserve change to sync_calificaciones

Pre-fix cleanup. This change from commit 6d7fb79 was surviving in the
working tree uncommitted. Isolate it so the pipeline fix does not mix
with it."
```

Why: the plan folder is untracked AND `sync_calificaciones_clickup.py`
is modified without a commit. Without T0, `git add` for the fix (T18)
would drag in unaudited changes from other work.

### T1 — `_parse_porcentaje` in `scripts/_parsing.py`

Create `domain/gestionar-cursos/scripts/_parsing.py` with the
`_parse_porcentaje` function described above. Shared module for future
parsing rules (Moodle uses different locales per institution).

### T2 — `cli_calificaciones.py:main()` reordered

Target diff:

```python
# BEFORE (lines ~485-516):
items = _parsear_gradebook(html)
json.dump(items, f, ...)              # JSON written OK
_imprimir_resumen(items)               # CRASHES here if all Pendiente
if args.dry_run:
    return                             # table NEVER printed in dry-run
for item in items:
    _actualizar_md_actividad(...)      # NEVER runs if table failed
_actualizar_snapshot(...)              # NEVER runs if table failed

# AFTER:
items = _parsear_gradebook(html)
json.dump(items, f, ...)
if not args.dry_run:                   # persist ONLY when not dry-run
    for item in items:
        _actualizar_md_actividad(...)
    _actualizar_snapshot(...)
try:
    _imprimir_resumen(items)           # print ALWAYS, even in dry-run
except Exception as e:
    console.print(f"[yellow]⚠ Resumen could not be printed: {e}[/yellow]")
```

Key: persistence moves INSIDE the existing `if not args.dry_run` block.
The summary prints always, wrapped in try/except.

### T3 — `cli_clickup.py` rewritten as local-plan

**Architectural change:** the script stops touching the ClickUp API.
It only produces the delta.

```python
# BEFORE (lines 280-330):
client = get_client()  # NameError, also violates C1
folder_id = _resolver_folder(client, ...)
# ... more calls that also do not work

# AFTER:
plan = {
    "_meta": {
        "periodo": periodo,
        "generated_at": datetime.now().isoformat(),
        "source": "moodle",
        "schema_version": 1
    },
    "to_create": [],
    "to_update": [],
    "to_archive": [],
    "unresolved": []
}

# Resolve locally (reads clickup.json, NOT the API):
folder = clickup_data.get("folder", {}).get("id")
if not folder:
    plan["unresolved"].append({"item": "folder", "reason": "clickup.folder.id is null"})

# Compare Moodle vs clickup.json locally:
for curso in cursos:
    list_id = curso.get("list_id")
    if not list_id:
        plan["unresolved"].append({"item": curso["key"], "reason": "clickup.list_id is null"})
        continue
    for actividad in actividades_moodle:
        task_id = _match_task(actividad, curso.get("tasks", []))
        if not task_id:
            plan["to_create"].append(_build_create(actividad, list_id))
        elif _needs_update(actividad, curso["tasks"][task_id]):
            plan["to_update"].append(_build_update(actividad, curso["tasks"][task_id]))

# Write the plan:
with open(plan_path, "w") as f:
    json.dump(plan, f, indent=2, ensure_ascii=False)
```

**Zero imports of `use-clickup`.** Zero HTTP calls. Just filesystem + JSON.

### T4 — `tests/conftest.py` with Rich mocks

```python
# tests/conftest.py
import sys, os
from unittest.mock import MagicMock
import pytest

# Pre-populate sys.path so `import cli_calificaciones` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

@pytest.fixture(autouse=True)
def mock_rich_console(monkeypatch):
    """Mock Rich's console so tests do not fail in CI without a TTY."""
    fake_console = MagicMock()
    fake_console.print = MagicMock()
    fake_console.log = MagicMock()
    monkeypatch.setattr("cli_calificaciones.console", fake_console)
    monkeypatch.setattr("cli_clickup.console", fake_console)
```

### T5, T6, T7 — Tests

T5 (`test_parsing.py`): exhaustive table of the 12+ formats listed in T1.

T6 (`test_cli_calificaciones.py`): reproduce the original bug
(all Pendiente) and verify persistence runs BEFORE the summary, even
in `--dry-run`.

T7 (`test_cli_clickup_plan.py`): runs `cli_clickup.py` with local
`snapshot.json` + `clickup.json` fixtures, verifies that the produced
`sync_plan.json` has the correct structure with `to_create` /
`to_update` / `to_archive` classified, without any HTTP call
(verifiable with `unittest.mock.patch("requests.get")` confirming it
is NOT called).

### T8 — `pyproject.toml`: add pytest to the existing array

```bash
# BEFORE (lines 20-25):
[dependency-groups]
dev = ["rich>=13.0", "ruff>=0.5", "ty>=0.0.1a5"]

# AFTER:
[dependency-groups]
dev = ["rich>=13.0", "ruff>=0.5", "ty>=0.0.1a5", "pytest>=8.0"]
```

Do NOT duplicate the `[dependency-groups]` block. Only add the item
to the array.

### T9 — SKILL.md refactor

Move to `references/` (see T11, T12) anything that is not an
operational directive:
- "Extraction Heuristics" (5 lines) → already links to
  `references/extraccion-heuristicas.md`, remove from SKILL.md.
- "Date Format" (10 lines) → consolidate in
  `references/fechas-fuente-de-verdad.md`.
- "Local Folder Structure" (40 lines) → `references/folder-structure.md`.
- "AGENTS.md - Contents" (35 lines) → `references/agents-md-template.md`.
- `foros` sub-flow (30 lines) → compress to 5 lines + link.

SKILL.md lands at ~440 lines, enough to add the "agent/skill contract"
block (~30 lines) without crossing 500.

### T10 — `references/sync-flow.md` (NEW, executable playbook)

KEY document of the fix. **This is not descriptive documentation —
it is the playbook the agent follows to apply the plan autonomously.**
Contains:

#### §A — Autonomous application (normal case, no human input)

Numbered steps the agent executes:

```
1. Read sync_plan.json
2. Verify _meta.schema_version (abort if != 1)
3. Verify orchestrator capabilities against _meta.orchestration_hint.tools_required
4. For each item in _meta.orchestration_hint.order:
   a. to_create:
      - Pre-check: GET /list/{list_id}/task?name=<name> to confirm absence
      - If a task with the same name exists: skip (idempotent)
      - If absent: POST /list/{list_id}/task with name+tags+priority+due_date_ms
   b. to_update:
      - Pre-check: GET /task/{task_id}/comment to read the latest comment
      - If the latest comment starts with "[calificaciones-auto]": skip (idempotent)
      - Verify diff.status.from against GET /task/{task_id}.status (race)
      - If divergence: log warning and abort THAT entry (not the whole plan)
      - If OK: PUT /task/{task_id} with non-null fields of diff
      - If diff.comment != null: POST /task/{task_id}/comment with comment.text
   c. to_archive:
      - Pre-check: GET /task/{task_id}.status
      - If status is already "cancelled": skip (idempotent)
      - PUT /task/{task_id} with status: "cancelled"
5. Log summary: applied / skipped / aborted / paused
```

#### §B — Pause for human input (the only case)

Only when `unresolved` contains items with **non-deterministic** reasons:

- `curso_no_inicializado` — the human must run `cli_init.py` first.
- `folder_not_found` — the human must create the folder in ClickUp
  manually.
- `task_id_ambiguo` — multiple near-match tasks; the human picks one
  or ignores.
- `list_id_null` — the course exists in Moodle but not in
  clickup.json; the human decides whether to run `cli_init.py` to
  initialize it.

The agent lists paused items in alphabetical order and reports the
full batch. It does NOT pause one at a time.

#### §C — PROHIBITED destructive actions

Explicit list the agent MUST NEVER execute:

- `DELETE /task/{id}` — the plan only plans `to_archive`, never
  `to_delete`.
- Reorganization of the ClickUp workspace (moving tasks between
  lists, changing folder hierarchy, renaming spaces).
- Editing custom statuses of the Universidad space.
- Any operation affecting tasks that are NOT in `sync_plan.json`
  (e.g. human manual tasks that did not come from Moodle).

If the agent detects that a required operation falls under §C, it
aborts THAT operation with an explicit error and continues with the
others.

#### §D — Known quirk: `status_id` vs `status` name

Lesson preserved from commit 6d7fb79 / 2026-2-B1. PUT /task/{id}
rejects `status_id` (numeric ID) with 400 Bad Request. ALWAYS send
`status` as the status name (e.g. `"calificado"`, `"pendiente"`,
`"cancelled"`).

#### §E — Idempotency table (for audit)

| Operation       | Key                       | Pre-check                                      |
|-----------------|---------------------------|------------------------------------------------|
| `to_create`     | `list_id + name`          | GET /list/{list_id}/task?name=X → empty?       |
| `to_update`     | `task_id`                 | GET /task/{id}/comment → no auto tag           |
| `to_archive`    | `task_id`                 | GET /task/{id}.status != "cancelled"?          |
| `unresolved`    | n/a                       | always requires intervention                   |

If the pre-check fails (already applied), silent skip. If the
pre-check passes but the PUT/POST operation fails, abort THAT entry
(not the whole plan) and record in `_meta.applied_results` (new
field in the post-apply plan).

### T13 — `CONTEXT.md` at root (NEW)

```markdown
## sync_plan

Declarative JSON artifact produced by `cli_clickup.py` that the agent
applies with `use-clickup`. Contains `to_create` / `to_update` /
`to_archive` / `unresolved`. NOT executed directly — the agent reads
it and orchestrates.

_Avoid_: "clickup delta", "clickup patch", "task list"

## delta

Difference between the current state of Moodle (source of truth) and
the current state of ClickUp, expressed as a `sync_plan`. Computed by
`cli_clickup.py`; applied by the agent.

_Avoid_: "pending changes", "diff", "patch list"

## agent-orchestrator

Entity (human or AI agent) that decides when to run `cli_estado.py`,
`cli_calificaciones.py`, `cli_clickup.py`, and `use-clickup`. It is
not a script — it is the policy layer.

_Avoid_: "the model", "the script", "the orchestrator"

## flow-direction

Architectural rule: data flows Moodle → Local → ClickUp, never the
other way. Reclassifications go as `to_update` of the same `task_id`;
deletions from Moodle go as `to_archive`, NOT `to_delete`.

_Avoid_: "bidirectional sync", "clickup as source", "reorganize"
```

### T14 — `LESSONS.md`: 3 new lessons

- **L8 (stale caches):** local caches (`calificaciones.json`,
  `snapshot.json`, `clickup.json`) can be hours or days old. The plan
  must not assume the `calificacion` it sees is current. The agent
  decides when to re-sync; the script only reports `_meta.stale_at`
  if the cache is >24h.
- **L9 (no-import rule between skills):** the fact that one domain
  skill USES another does not mean it must import it. `use-clickup`
  is an API the agent invokes, not a library the skill links.
  Cross-imports break the composition rule and make skills not
  independently deployable.
- **L10 (ClickUp is terminal):** ClickUp is not reorganized from
  code. Renames, reclassifications, physical deletions are manual
  operations. The script plans changes; it does not execute them.
  The human owns the structure of their workspace.

### T15 — Visual browser validation

Discipline, not code. Before marking T17 (pytest) as done:

1. Launch Chrome with `--remote-debugging-port=9222` (already done by
   `navegador_cdp.py`).
2. Connect via CDP and navigate to the gradebook of a test course.
3. Capture a screenshot of the gradebook with all items in
   "Pendiente" — confirms that `_parse_porcentaje` covers real
   formats.
4. Run `cli_calificaciones.py --dry-run` and verify the console
   output matches expectations.
5. For ClickUp: open the real panel in the browser, compare against
   the produced `sync_plan.json`. Verify the `task_id`, `list_id`,
   `status`, `tags` the plan says match what ClickUp shows.

If visual validation reveals uncovered formats, iterate on T1.

## §V VERIFICATION (post-build)

```bash
cd /Users/andres.rendon/Documents/Projects/agent-skills
uv sync --project domain/gestionar-cursos --dev
cd domain/gestionar-cursos

# Unit tests
uv run pytest -v
# → exit 0 (D6)

# Audit
uv run python ../../utility/skill-forge/scripts/audit.py gestionar-cursos
# → exit 0 (D7)

# Manual end-to-end
cd /Users/andres.rendon/Documents/Universidad/2026-2-B1
uv run --project ~/.agents/skills/gestionar-cursos \
  python ~/.agents/skills/gestionar-cursos/scripts/cli_calificaciones.py \
  "2607B04G1-lenguaje-de-programación-avanzado-1"
# → exit 0 (D1)
# → snapshot.json has calificacion for every activity (D2)
# → .md files have ## Calificación (D3)

uv run --project ~/.agents/skills/gestionar-cursos \
  python ~/.agents/skills/gestionar-cursos/scripts/cli_clickup.py .
# → exit 0 (D4)
# → clickup.json has _meta + sync_plan with all 4 sections (D5)
# → zero HTTP requests to api.clickup.com
```

**Deploy (OUT of this plan, post-merge):**
```bash
skills add arendon1/agent-skills -a hermes-agent -g -y --skill gestionar-cursos
```

## §R REFS

- PRD.md — requirements
- LESSONS.md — lessons (existing L1-L7 + new L8-L10)
- AGENTS.md at root — constitution (§3, §9, §11, §15)
- `use-clickup/scripts/client.py` — API consumed by the agent
- `/tmp/agy_review_prompt.md` — adversarial review transcript
- `/Users/andres.rendon/.hermes/cache/delegation/live/deleg_fe8dd1fd/`
  — subagent review transcript
