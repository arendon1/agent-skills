---
name: dispatch
description: |
  Dispatch fresh subagents for independent tasks, with two-stage review (spec
  compliance, then code quality). Use when a plan has independent tasks that can
  run in parallel, or when a task is large enough to benefit from an isolated
  subagent.
  Use when the user says "parallel", "dispatch", "subagent", or when the plan has
  independent tasks, or when a task is large enough to benefit from isolation.
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# dispatch — parallel subagents with two-stage review

Dispatch fresh subagents for independent tasks. Each subagent gets isolated
context (you construct exactly what it needs — it never inherits your session's
history), implements its task, and commits. Then a two-stage review: spec
compliance, then code quality. A broad final review at the end.

## WHEN (self-trigger)

- The `build` loop detects a parallelizable set in `PLAN.md §N`.
- The user says "parallel", "dispatch", "subagent", "run these concurrently".
- A task is large enough to benefit from an isolated subagent (high context cost
  if done in the main thread).

Skip when tasks are tightly coupled — single-thread `build` is better then.

## WHY SUBAGENTS

You delegate tasks to specialized agents with isolated context. By precisely
crafting their instructions and context, you ensure they stay focused and succeed.
They never inherit your session's context or history — you construct exactly what
they need. This also preserves your own context for coordination work.

**Core principle:** fresh subagent per task + task review (spec + quality) + broad
final review = high quality, fast iteration.

## CONTINUOUS EXECUTION

Do not pause to check in with the user between tasks. Execute all dispatched tasks
without stopping. The only reasons to stop: BLOCKED status you cannot resolve,
ambiguity that genuinely prevents progress, or all tasks complete. "Should I
continue?" prompts and progress summaries waste the user's time — they asked you
to execute, so execute.

## THE PROCESS

### Per task

1. **Construct the implementer prompt.** Give the subagent exactly: the task (`§T.n`
   row from `PLAN.md`), the cited invariants (`§V`) and interfaces (`§I`) it serves,
   the test it must pass (from the task's `test` column), the relevant code paths,
   and the commit convention. Do NOT give it your session history.
2. **Dispatch the implementer subagent.** It implements (via `tdd`), tests, commits
   (conventional commit `T<n>: ...`), and self-reviews against the task spec.
3. **Write a diff file** of what the subagent did.
4. **Dispatch the task-reviewer subagent** with the diff + the task spec. Two-stage
   review:
   - **Spec compliance** — did the subagent do what `§T.n` + `§V` + `§I` require?
   - **Code quality** — does the code verify behavior through public interfaces,
     respect invariants, avoid shallow abstractions?
5. **If the reviewer reports Critical/Important findings:** dispatch a fix subagent
   with the findings. Repeat until the reviewer approves.
6. **Mark the task `[x]` in `PLAN.md`** and record progress in the ledger.

### Broad final review

After all tasks complete, dispatch a broad whole-branch reviewer that checks the
cumulative diff against the full plan (not task-by-task). This catches integration
issues single-task reviews miss. Hand the final review's findings to the `review`
loop if any are BLOCK.

## IMPLEMENTER PROMPT — what to include

Construct the subagent's context precisely. Include:
- The exact `§T.n` row (task, cites, test, blocked-by).
- The full text of every cited `§V` invariant and `§I` interface.
- The relevant `CONTEXT.md` terms (canonical names it must use).
- The relevant code paths (file:line) it will touch.
- The verification command (the oracle) it must run.
- The commit convention: `T<n>: <goal line> (<§V cites>)`.
- Instruction to use `tdd` (failing test first), then `verify` before claiming done.

Do NOT include: your session history, other tasks' context, or your own hypotheses
about how to implement. The subagent implements fresh from the spec.

## TASK-REVIEWER PROMPT — the two stages

1. **Spec compliance:** Does the diff satisfy every cited `§V`? Does it preserve
   every cited `§I` shape? Does the named test exist and pass? Cite evidence
   (file:line) for each claim.
2. **Code quality:** Do the tests verify behavior (good) or implementation (bad)?
   Are there shallow abstractions? Hidden coupling? Missing error handling for the
   edge cases `§V` names? Cite evidence.

Findings classified: Critical (blocks merge) / Important (should fix) / Minor
(note). Critical/Important -> fix subagent. Minor -> note in the ledger.

## BOUNDARIES

- MUST construct each subagent's context precisely (no session-history inheritance).
- MUST run the two-stage review (spec compliance + code quality) per task.
- MUST run the broad final review at the end.
- MUST NOT pause for user check-ins between tasks (continuous execution).
- MUST stop only on BLOCKED, ambiguity, or all-complete.
- MUST hand BLOCK findings to the `review` loop.
- MUST use `caveman` for the ledger and `CONTEXT.md` canonical terms in prompts.
