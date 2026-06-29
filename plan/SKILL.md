---
name: plan
description: |
  Break a PRD/ARD/SPEC into an implementation plan of vertical-slice tasks. Each
  task cites the invariants and interfaces it touches, names the test that proves
  it, and has a status cell. Sole mutator of PLAN.md in the active plan.
  Use when ready to break requirements into tasks, after grill/design/spec and
  before build, or when the user says "plan this", "break this down", "tasks",
  "what's the plan".
invocation: user
layer: process
loop: plan
deliverable: PLAN.md in the active plan folder
metadata:
  version: "1.0.0"
---

# plan — requirements into PLAN.md

Break a PRD/ARD/SPEC into an implementation plan of vertical-slice tasks. Each
task is a tracer bullet: thin but complete, cutting through every integration
layer end-to-end, demoable on its own. Each task cites the invariants and
interfaces it serves and names the test that proves it.

Vertical slices, not horizontal layers. A task "add the database layer" is
wrong; a task "POST /x returns 200 {id} persisted" is right.

## OWNERSHIP

Owns: `PLAN.md` in the active plan folder.
Reads: `PRD.md`, `ARD.md`, `SPEC.md` (whatever exists), `CONTEXT.md`, the codebase.
Hands off to: `build` (executes tasks, flips status cells only).
MUST NOT write `PRD.md`, `ARD.md`, `SPEC.md`, or `LESSONS.md`.

`build` flips `PLAN.md` task status cells (`[ ]` -> `~` -> `[x]`) but MUST NOT
rewrite other PLAN.md content. `plan` is the sole author of task rows.

## WHEN (user-invoked)

- After `grill` / `design` / `spec` produced enough to break into tasks.
- User says "plan this", "break this down", "tasks", "what's the plan".
- Existing `PLAN.md` needs new tasks appended (re-plan a slice).

## STEP 0 — READ EXISTING STATE

1. Resolve the active plan per §6. If none, ask the user to run `grill` first.
2. Read whatever exists: `PRD.md`, `ARD.md`, `SPEC.md`. At minimum a PRD.
3. Read `CONTEXT.md` — name tasks using canonical terms.
4. Explore the codebase for existing seams. Prefer existing seams over new ones.
   Look for prefactoring opportunities: "make the change easy, then make the easy
   change."

## STEP 1 — DRAFT VERTICAL SLICES

Break the objective into **tracer bullet** tasks. Each task:

- Cuts through ALL integration layers end-to-end (schema, API, UI, tests).
- Delivers a narrow but COMPLETE path. A completed task is demoable/verifiable alone.
- Has one clear acceptance: name the test that proves it.
- Cites the invariants (`§V`) and interfaces (`§I`) it serves.
- Names its blockers (which tasks must complete first).

A task that is a single layer ("write the schema") is a horizontal slice — merge
it into a vertical slice that proves it end-to-end. Prefactoring that must happen
first is its own task, marked as blocking.

## STEP 2 — ORDER BY DEPENDENCY

Order tasks so a task's blockers come before it. Publish in dependency order so
references are real. If two tasks are independent, either order is fine — flag
them as parallelizable for the `dispatch` discipline.

## STEP 3 — QUIZ THE USER

Present the proposed breakdown as a numbered list. For each task show:
- **Title** — short, uses canonical terms.
- **Cites** — `§V.N`, `§I.N` it serves.
- **Test** — the test name that proves it (e.g. `TestV2_TokenExpiryRejected`).
- **Blocked by** — which tasks must complete first (if any).

Ask the user:
- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?

Iterate until the user approves the breakdown.

## STEP 4 — WRITE PLAN.md

Write `PLAN.md` using `caveman`. Template:

```markdown
# PLAN — <slug>

## §T TASKS

id|status|task|cites|test|blocked by
T1|[ ]|<task 1, vertical slice>|V1,I.api|TestV1_...|-
T2|[ ]|<task 2>|V2|TestV2_...|T1
T3|[ ]|<task 3, parallelizable with T2>|V3|TestV3_...|T1

## §N NOTES
- <prefactoring note>
- <parallelizable set: T2, T3 — dispatch candidate>
```

Table cell rules: literal `|` -> escape as `\|`. Backticks OK. Cells trimmed.
Empty = `-`. Status: `[ ]` todo, `~` wip, `[x]` done.

### Task ID rules

- Monotonic — `T1, T2, T3, ...`. Never reuse an ID, even after deletion. If `T2`
  is dropped, the next task is `T4`, not a renumbered `T2`.
- `cites` column lists `§V`/`§I` deps: `V2,I.api`.
- `test` column names the test that proves the task. A task without a test is a
  lie — every task MUST have one. (Prefactoring tasks may cite an existing test
  that must still pass.)
- `blocked by` lists task IDs that must be `[x]` first, or `-`.

## RIGHT-SIZE

- One-line fix: `PLAN.md` with a single `T1`. Skip PRD/ARD/SPEC entirely.
- Small feature: `PLAN.md` with 1-3 tasks, thin cites.
- Medium feature: full task table with cites + tests + blockers.
- Complex / high-blast-radius: full task table + `§N` notes for prefactoring,
  parallelizable sets, and dispatch candidates.

## WHEN TO STOP

Done when:
- Every task is a vertical slice with a named test and cited invariants.
- Dependencies are correct and the user approved.
- Task IDs are monotonic.
- Canonical terms are used throughout.
- Parallelizable sets are flagged in `§N` for `dispatch`.

## HANDOFF

Tell the user: `build` next (executes tasks in order, invoking `tdd` per task,
flipping status cells, running `verify` before declaring each task done).

## BOUNDARIES

- MUST NOT write `PRD.md`, `ARD.md`, `SPEC.md`, or `LESSONS.md`.
- MUST NOT create a task without a test. Every task names its proof.
- MUST NOT produce horizontal-layer tasks. Vertical slices only.
- MUST get user approval on the breakdown before writing `PLAN.md`.
- MUST use `caveman` and `CONTEXT.md` canonical terms.
