---
name: check
description: |
  Read-only drift detector. Diffs the plan artifacts against the current code and
  reports violations grouped by severity. Writes nothing — suggests remedies but
  never invokes them.
  Use when checking drift, auditing the spec, verifying invariants hold, or when
  the user says "check drift", "audit the spec", "does the code still match", "spec
  vs code", "is the plan still accurate".
invocation: user
layer: process
loop: check
deliverable: drift report (read-only, suggests remedies, writes nothing)
metadata:
  version: "1.0.0"
---

# check — drift report

Pure diagnostic. Reports violations grouped by severity. Writes nothing. The user
decides the remedy.

Plan artifacts drifting silently from code is the #1 failure mode. `check` is the
detector. Run it after each `build` and before each ship — drift caught here is a
diff; drift caught in prod is a `LESSONS.md` bug row.

## OWNERSHIP

Owns: the drift report (delivered inline — does NOT write a file).
Reads: `PLAN.md`, `SPEC.md`, `ARD.md` (whatever exists), `CONTEXT.md`, the codebase.
MUST NOT write anything. NEVER invokes fix skills — only suggests them.

## WHEN (user-invoked)

- After a `build` completes a task or a plan.
- Before a ship / merge / PR.
- User asks "check drift", "audit the spec", "does the code still match", "is the
  plan still accurate".
- Invoked by the `verify` discipline as the final plan-level drift check.

## STEP 0 — LOAD

1. Resolve the active plan per §6. If none, "no plan, nothing to check." Stop.
2. Read whatever exists: `PRD.md`, `ARD.md`, `SPEC.md`, `PLAN.md`, `CONTEXT.md`.
3. Parse invocation args:
   - `§V` -> check invariants only (default)
   - `§I` -> check interfaces
   - `§T` -> audit task status vs code
   - `--all` -> all three

## CHECK §V — invariants

For each `V<n>` in `SPEC.md`/`ARD.md`:

1. Translate the invariant into a verifiable claim about the code.
2. Grep / read the relevant files.
3. Classify:
   - **HOLD** — the code satisfies the invariant.
   - **VIOLATE** — the code breaks the invariant (cite file:line).
   - **UNVERIFIABLE** — no test covers the invariant's path.
4. Record the address + file:line evidence.

## CHECK §I — interfaces

For each `§I` item:

1. Locate the implementation.
2. Classify:
   - **MATCH** — shape in code = shape in spec.
   - **DRIFT** — impl exists, shape differs (cite file:line).
   - **MISSING** — impl absent.
   - **EXTRA** — code exposes a surface not in `§I`.

## CHECK §T — tasks

For each `T<n>` in `PLAN.md`:

1. If `[x]`: verify the claimed work is present in the code. If not -> **STALE**.
2. If `~`: note as in-progress.
3. If `[ ]`: note as pending.

## REPORT

Caveman. Grouped by severity. Example:

```
## §V drift
V2 VIOLATE: auth/mw.go:47 uses `<` not `<=`. see LESSONS.md B.1.
V5 UNVERIFIABLE: no test covers every req path.

## §I drift
I.api DRIFT: POST /x returns `{result}` not `{id}`. route.go:112.
I.cmd MISSING: `foo bar` absent from cli/*.go.

## §T drift
T3 STALE: status [x], no middleware file exists.

## summary
2 violate. 1 missing. 1 stale. 1 unverifiable.
next: spec skill with `bug:` or fix code at cited lines.
```

## REMEDY HINTS (not actions)

End the report with a one-line hint per class. NEVER invoke the fixes.

- VIOLATE / DRIFT -> invoke the `spec` skill with `bug: <V.n>` or fix the code.
- MISSING -> invoke the `build` skill on `§T.n` if a task exists; else the `spec`
  skill with `amend §T`.
- STALE -> the `spec` skill with `amend §T` to uncheck.
- EXTRA -> the `spec` skill with `amend §I` to document, or delete the code.
- UNVERIFIABLE -> the `tdd` discipline to write the missing test.

## BOUNDARIES

- MUST write nothing. No artifact edits. No code edits.
- MUST NOT invoke fix skills. Report only.
- MUST cite file:line for every VIOLATE / DRIFT / STALE finding.
- MUST run on the main thread — no subagents.
- MUST give a binary verdict per item: holds or drifts. No scores, no grades.
- MUST use `caveman` for the report.
