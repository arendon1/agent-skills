# LESSONS — fix(gestionar-cursos)

## L1 — The `float("-" or 0)` bug is a classic Python trap

- **Symptom:** `ValueError: could not convert string to float: '-'`
- **Cause:** `valor or 0` only catches `valor == ""` or `valor is None`.
  Any non-empty string (including `"-"`, `"N/A"`, `"—"`) is truthy.
- **Learning:** `or 0` is NOT defensive for "any non-parseable string".
  You need an explicit list of sentinels.
- **Portable:** prefer `_parse_porcentaje()` with an explicit sentinel
  list over an inline expression.

## L2 — "Imaginary" dependencies are a code smell

- **Symptom:** `NameError: name 'get_client' is not defined` on first
  use.
- **Cause:** the script called functions from `use-clickup` without
  importing them. The "delegated to the agent" comment hid the debt.
- **Learning:** a script structured as an end-to-end executable MUST be
  end-to-end executable. Otherwise, the comment lies.
- **Portable:** either implement the full wiring, or remove the
  `--apply` option and document the script as "preview only".

## L3 — The order of operations in main() matters when there is a cosmetic step

- **Symptom:** `_imprimir_resumen` crashed before
  `_actualizar_md_actividad` and `_actualizar_snapshot`, losing the
  extraction work.
- **Cause:** order collect → persist → format(report) → persist2; the
  second persistence was skipped if format blew up.
- **Learning:** persist first, format after. Formatting is for the
  human; the data on disk is for the system.
- **Portable:** canonical order collect → persist → format → report.

## L4 — Search before assuming

- **Context:** the "status_id vs status name" lesson was already
  documented in `sync_calificaciones_clickup.py:24-28`. When
  implementing fix B4, the answer was literally in the neighboring
  skill's file.
- **Learning:** before implementing a fix, search the repo for
  existing notes about the bug.
  `grep -r "leccion\|lesson\|LPA\|gotcha" --include="*.md"`.

## L5 — The raw HTML gradebook (295 KB) stays on disk even if the script fails

- **Context:** `_descargar_gradebook` writes the HTML BEFORE parsing.
  If the parser fails, the HTML is orphaned in `_cache/`.
- **Decision:** NOT included in this fix (out of scope). Documented as
  a known issue. Separate plan if worth it.

## L6 — The minimum viable test protects against future regressions

- **Learning:** the cost of adding the minimum test (3 functions,
  ~20 lines) is negligible compared to the cost of diagnosing the
  bug in production. Add tests with each fix, not as a separate task.

## L7 — The agent is the real orchestrator — but only if it has the primitives

- **Learning:** "delegate to the agent" works only if the agent has
  the primitives available. Today the `use-clickup` skill DOES have
  them. The problem was that `cli_clickup.py` did not expose them.

## L8 — Local caches can be stale

- **Symptom:** a skill that depends on local files (`snapshot.json`,
  `calificaciones.json`, `clickup.json`) may be reading information
  that is hours or days old. The delta it produces against ClickUp
  can be based on stale reality.
- **Cause:** there is no "last fresh sync" timestamp in the local
  artifacts. The script does not know when Moodle was last actually
  read.
- **Learning:** state-management scripts must REPORT the age of their
  input (`_meta.source_fetched_at`, `_meta.stale`), not just process
  it. The agent decides when to re-sync; the script only reports.
- **Portable:** every artifact with `_meta.generated_at` should be
  paired with `_meta.source_freshness` or a configurable "stale"
  threshold. E2E tests must include the "48h cache + 1 change in
  Moodle" case.

## L9 — The no-import rule between domain skills

- **Context:** `gestionar-cursos` needs `use-clickup` to sync tasks.
  The first reading was "import get_client" — but that reading
  violates the composition principle: every skill must be
  independently deployable, without requiring another skill to be
  installed in the same path.
- **Cause:** the temptation to "reuse" the already-built HTTP client
  instead of producing an artifact the agent applies with the right
  tool.
- **Learning:** the fact that skill A USES skill B does not mean it
  must import it. `use-clickup` is an API the agent invokes, not a
  library the skill links. The contract between skills is the JSON
  artifact the first produces and the second (via the agent)
  consumes.
- **Portable:** when skill A needs capabilities from skill B, the
  pattern is: A produces a declarative artifact (JSON, YAML)
  describing what it wants to do; the agent reads the artifact and
  uses B to apply it. A never imports B. B never knows A exists.
- **Opposite anti-pattern:** "skill A is useful without skill B" —
  true, but "skill A requires skill B in its import path" breaks
  independent deployability. Test:
  `cd /path/to/A && uv run python A/script.py` without B present
  must fail CLEANLY (clear message), not with `ModuleNotFoundError`
  at runtime.

## L10 — ClickUp is terminal; it is not reorganized from code

- **Context:** the original plan proposed "delete + create" for
  activities that change name or type between Moodle and ClickUp.
  The user corrected: ClickUp is where the human organizes their
  work, not a state the script can arbitrarily reorganize.
- **Cause:** the temptation to "clean up" the ClickUp workspace when
  Moodle reflects a change. It assumes ClickUp is just another
  database.
- **Learning:** ClickUp is terminal in the flow. Changes in Moodle
  produce `to_update` (PUT with diff) or `to_archive` (status
  cancelled, NEVER DELETE). Renames, reclassifications, merges,
  splits are human decisions in their workspace.
- **Portable:** in general, every system where the human is the final
  owner of state should receive `to_update` / `to_archive`, not
  `to_delete + to_create`. The human's history is sacred.
- **Design implication:** the `sync_plan.json` schema includes
  `to_archive` with a `reason` field (free string:
  "removed_from_moodle", "renamed_in_moodle", "superseded") so the
  human can audit why a task ended up in the cancelled state.

## L11 — Maximum agent autonomy, pause only for destructive input

- **User rule (2026-07-21):** "this skill must allow agents maximum
  autonomy when the user has given them some instruction. The goal
  is always to fulfill with minimum human interaction, unless a
  critical situation warrants it, such as some kind of destructive
  action."

- **Reason for the rule:** the human is the bottleneck. Every time
  the agent pauses to ask for confirmation, the main value of
  automation is lost. Agents can read context, do pre-checks, and
  detect non-deterministic ambiguity — use them before asking.

- **Design implication #1:** `sync_plan.json` carries
  `_meta.orchestration_hint` with `order`, `tools_required`, and
  `pause_for_human`. The agent does not have to guess the sequence or
  the capabilities — it reads them from the plan.

- **Design implication #2:** `references/sync-flow.md` is an
  **executable playbook** (numbered steps, not descriptive
  documentation). The agent reads it once, executes, reports. It
  does NOT improvise.

- **Design implication #3:** `references/sync-flow.md` §C declares
  PROHIBITED destructive actions. The agent aborts THAT operation if
  it falls under §C; it does not ask the human. The prohibition is
  already in the playbook.

- **Design implication #4:** SKILL.md explicitly declares
  `Operation mode: autonomous by default` so the agent's first read
  does not generate the question "should I ask the human?".

- **Portable:** every skill that produces artifacts for an agent
  should declare its operation mode (autonomous / collaborative /
  manual) in the frontmatter or in a visible section of SKILL.md.
  Ambiguity about "may I execute without asking?" is the main cause
  of unnecessary friction.

- **Exceptions that DO justify a human pause:**
  - Destructive operation not listed in §C (unplanned DELETE,
    modification of custom status, etc.).
  - Race conflict where the real state diverges from `diff.from` and
    how to resolve it is non-deterministic.
  - `unresolved` with a non-deterministic reason (listed in §B of
    sync-flow.md).
  - Missing required capability (`tools_required` of the plan).
