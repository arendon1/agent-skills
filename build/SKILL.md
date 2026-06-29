---
name: build
description: |
  Execute a plan against the active plan folder. Native single-thread loop: per
  task, flip status, implement via TDD, verify, commit. Auto-invokes tdd, verify,
  lessons, git, and dispatch on failure or when parallelizable sets appear.
  Use when the user asks to build, implement, or tackle a task, says "build §T.3",
  "run the build", or "do the next task".
invocation: user
layer: process
loop: build
deliverable: working verified code + PLAN.md tasks flipped to x
metadata:
  version: "1.0.0"
---

# build — execute the plan

Single-thread native plan-then-execute. No swarm. You are the main agent; you may
dispatch parallel work to subagents only when the plan flags an independent set
(via the `dispatch` discipline).

## OWNERSHIP

Owns: `PLAN.md` task status cells (flips `[ ]` -> `~` -> `[x]`) — and nothing else
in the plan artifacts.
Reads: `PLAN.md` (required), `PRD.md`/`ARD.md`/`SPEC.md` (whatever exists),
`CONTEXT.md`, the codebase.
MUST NOT rewrite `PRD.md`, `ARD.md`, `SPEC.md`, `LESSONS.md`, or `PLAN.md` task
content. Only status cells.

## WHEN (user-invoked)

- User says "build", "implement", "execute the plan", "run the build".
- User names a task: "build §T.3", "do T2".
- User says "do the next task", "--next", "implement next".

## STEP 0 — LOAD

1. Resolve the active plan per §6. If none, tell the user to run `grill` + `plan`
   first. Stop.
2. Read `PLAN.md`. If absent, tell the user to run `plan`. Stop.
3. Read whatever else exists: `PRD.md`, `ARD.md`, `SPEC.md`, `CONTEXT.md`, `§R`
   (research) if present — external facts the build MUST honor.
4. Parse the invocation:
   - `§T.n` / `T<n>` → that task only.
   - `--next` / "next" → lowest-numbered task with status `[ ]` or `~`.
   - `--all` / empty → every `[ ]` task in `§T` order.

### Right-size gate

High blast radius (shared module, auth, data, money, public interface)? Run the
`review` loop first. Trivial and reversible? Skip planning ceremony, go to EXECUTE.

## STEP 1 — PLAN (per chosen task)

Native plan mode — the agent's own task breakdown, not a new artifact. For each
chosen task:

1. Cite every `§V` invariant that applies. The plan MUST respect all.
2. Cite every `§I` interface touched. The plan MUST preserve shape.
3. List files to create / edit.
4. **Verification contract** — name the EXACT test(s) that prove each `§V` touched.
   Which test, not "add tests". Each `§V` touched -> a named test that fails first.
   (This is what the `tdd` discipline will write.)
5. Name the verification command (test, build, lint) — the external oracle.
   Green = done; NEVER "looks done".

Show the plan. Wait for user OK unless the user said "auto" / "go".

### Independent-set detection

If the chosen tasks include a parallelizable set (flagged in `PLAN.md §N`), and
the work would benefit from isolation, invoke the `dispatch` discipline to farm
the independent tasks to subagents. Otherwise, single-thread.

## STEP 2 — EXECUTE (per task, in dependency order)

For each task in order:

1. Flip `§T.n` status cell `[ ]` -> `~`. Write only that cell.
2. Invoke the `tdd` discipline: write the failing test named in the verification
   contract, watch it fail, write minimal code to pass, watch it pass.
3. Run the verification command (the oracle).
4. **Pass** → flip `~` -> `[x]`. Commit (invoke the `git` discipline:
   `T<n>: <goal line>` + `§V` cites). Next task.
5. **Fail** → invoke the `debug` discipline, then the `lessons` reflex. Do NOT
   retry blindly. See FAIL below.

## STEP 3 — FAIL → DEBUG → LESSONS

On test/build failure:

1. Invoke the `debug` discipline — build a tight feedback loop, reproduce,
   hypothesize, instrument, fix. Do not guess.
2. When the root cause is found, invoke the `lessons` reflex: ask
   "would a new `§V` invariant catch this class of bug?"
   - If yes → `lessons` appends the `§B` row + the new `§V` to `LESSONS.md` /
     `SPEC.md`, and writes the regression test. Then resume `build` against the
     updated spec.
   - If no (one-time typo, external dep) → `lessons` still appends the `§B` row.

Rule: NEVER silently fix root-cause without considering `lessons`. `LESSONS.md`
is the memory that stops recurrence (see the `lessons` skill).

## STEP 4 — VERIFY (before declaring done)

A task is `[x]` only if (invoke the `verify` discipline):
- The verification command (the oracle) exits 0, run fresh in this session.
- Every `§V` touched has its named test from the verification contract, and it passes.
- No `§V` invariant regressed (run the full test suite at the end of the task,
  and again at the end of the whole plan).

## STEP 5 — COMPLETE

After all chosen tasks are `[x]`:
- Run the full test suite + lint + build. All green.
- Invoke the `verify` discipline on the whole plan.
- Invoke the `git` discipline: present options (merge, PR, keep branch).
- Tell the user: plan complete. Optionally archive the plan folder to
  `docs/plans/archive/`.

## WRITE POLICY

- Only flip `§T` status cells in `PLAN.md`. No other artifact edits from `build`.
- Other spec edits → invoke `spec`. Other invariant additions → `lessons`.
- Commit after each `§T` completes. Message: `T<n>: <goal line>` + `§V` cites.

## NON-GOALS

- No speculative work beyond chosen task scope.
- No progress dashboards. `grep '|~|' PLAN.md` is the dashboard.
- No silent fixes. Every failure routes through `debug` + `lessons`.
- No completion claims without fresh verification evidence (the `verify` Iron Law).

## BOUNDARIES

- MUST NOT rewrite `PRD.md`, `ARD.md`, `SPEC.md`, `LESSONS.md`, or `PLAN.md` task
  content. Status cells only.
- MUST NOT declare a task `[x]` without running the verification command fresh.
- MUST NOT retry a failure blindly. Route through `debug` then `lessons`.
- MUST commit after each task (via the `git` discipline).
- MUST use `caveman` for any artifact touches and `CONTEXT.md` canonical terms.
