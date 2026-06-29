---
name: verify
description: |
  Completion gate. Ensure work is actually done before declaring it complete.
  Verify against the plan, run the full suite, confirm no regressions, check
  artifacts are updated. Evidence before assertions, always.
  Use when about to mark a task, plan, or objective complete, or when the user
  says "done", "complete", "finished", "ready to ship", "is this done".
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# verify — completion gate

Ensure work is actually done before declaring it complete. Verify against the
plan, run the full suite, confirm no regressions, check artifacts are updated.

Claiming work is complete without verification is dishonesty, not efficiency.

## WHEN (self-trigger)

- About to mark a `PLAN.md` task `[x]`.
- About to declare a plan or objective complete.
- About to commit, merge, or open a PR.
- User says "done", "complete", "finished", "ready to ship", "is this done".
- Invoked by the `build` loop before each task's status flips to `[x]`.

## THE IRON LAW

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this session, you cannot claim it
passes. "Should work", "probably passes", "I'm confident" are not evidence.

## THE GATE FUNCTION

Before claiming any status or expressing satisfaction:

1. **IDENTIFY** — what command proves this claim?
2. **RUN** — execute the FULL command (fresh, complete). Not a partial check.
3. **READ** — full output, check exit code, count failures.
4. **VERIFY** — does the output confirm the claim?
   - If NO → state actual status with evidence. Do not claim done.
   - If YES → state the claim WITH evidence (paste the command + result).
5. **ONLY THEN** — make the claim.

Skip any step = lying, not verifying.

## COMMON FAILURES

| Claim | Requires | Not sufficient |
|---|---|---|
| Tests pass | test command output: 0 failures | previous run, "should pass" |
| Linter clean | linter output: 0 errors | partial check, extrapolation |
| Build succeeds | build command: exit 0 | linter passing, logs look good |
| Bug fixed | original symptom test: passes | code changed, assumed fixed |
| Regression test works | red-green cycle verified | test passes once |
| Task done | every `§V` touched has its named test passing | "I implemented it" |
| Plan complete | all `§T` tasks `[x]` + full suite green | most tasks done |
| Requirements met | line-by-line checklist against PRD/SPEC | tests passing |

## RED FLAGS — STOP

- Using "should", "probably", "seems to".
- Expressing satisfaction before verification ("done!", "perfect!", "great!").
- About to commit/push/PR without verification.
- Trusting a subagent's "success" report without re-running the oracle.
- Relying on partial verification.
- Thinking "just this once".
- Tired and wanting work to be over.
- ANY wording implying success without having run verification.

## RATIONALIZATION PREVENTION

| Excuse | Reality |
|---|---|
| "Should work now" | RUN the verification. |
| "I'm confident" | Confidence is not evidence. |
| "Just this once" | No exceptions. |
| "Linter passed" | Linter is not the test suite. |
| "It compiled" | Compiling is not passing. |
| "The subagent said it passed" | Re-run the oracle yourself. |

## TASK-LEVEL VERIFICATION (invoked by build)

A `PLAN.md` task is `[x]` only if ALL hold:
- The verification command (the oracle named in the task's `test` column) exits 0,
  run fresh in this session.
- Every `§V` invariant the task cites has its named test passing.
- No `§V` invariant regressed (the full test suite is green).
- The task's acceptance criterion is demonstrably met (paste the evidence).

If any fails, the task stays `~` (wip). Do not flip to `[x]`.

## PLAN-LEVEL VERIFICATION (before declaring the plan complete)

Before declaring the plan complete, run ALL of:
1. Full test suite — green.
2. Lint — clean.
3. Build — exit 0.
4. Every `§T` task in `PLAN.md` is `[x]`.
5. Every `§V` invariant in `SPEC.md`/`ARD.md` has a passing test.
6. `LESSONS.md` `§B` rows: every bug found during the build has a fix commit
   (no `-` in the fix column for bugs that occurred during this build).
7. `CONTEXT.md` reflects any new terms coined during the build.
8. No drift: run the `check` discipline (read-only drift detector) against the
   plan artifacts and the code. Zero `FAIL` findings.

Present the evidence to the user as a compact block:

```
verify: <plan slug>
- tests:      PASS (N tests, 0 failures)  [paste command]
- lint:       PASS (0 errors)              [paste command]
- build:      PASS (exit 0)               [paste command]
- tasks:      [x] T1..T5 (5/5)
- invariants: V1..V7 all have passing tests
- lessons:    §B clean (no unfixed bugs)
- drift:      PASS (check discipline, 0 FAIL)
-> PASS ready to ship
```

If any line is not PASS, the plan is not complete. State what is missing.

## BOUNDARIES

- MUST run the verification command fresh in this session before claiming done.
- MUST paste the command + result as evidence. No evidence = no claim.
- MUST NOT declare a task `[x]` if any cited invariant's test fails.
- MUST NOT declare a plan complete with any task still `[ ]` or `~`.
- MUST NOT trust subagent reports without re-running the oracle.
- MUST run the `check` discipline before declaring a plan complete.
- MUST use `caveman` for the evidence block.
