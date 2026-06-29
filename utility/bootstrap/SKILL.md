---
name: bootstrap
description: |
  Session enabler. Teaches the agent to check for and invoke relevant skills before
  any response, and to check for project artifacts (CONTEXT.md, active plan folder).
  Use when a session starts or after a compaction resets context. Injected at session
  start and after compaction. The only bootstrap-invoked skill.
invocation: bootstrap
layer: utility
metadata:
  version: "1.0.0"
---

# bootstrap — session enabler

The only `bootstrap`-invoked skill. Injected by the adapter at session start and
after compaction. Teaches two habits: (1) check for and invoke relevant skills
before any response, and (2) check for project artifacts (`CONTEXT.md`, active
plan folder) and keep them updated.

This is the skill that makes the system self-triggering. Without it, the other
skills sit unused.

## WHEN (bootstrap-invoked)

Injected at:
- `session_start` — a new session begins.
- `session_compact` — context was compacted; re-establish the habits.

Not user-invoked. Not model-invoked. Only the adapter injects it.

## HABIT 1 — CHECK FOR AND INVOKE RELEVANT SKILLS

Before any response (including clarifying questions), check whether a skill might
apply. If there is even a small chance a skill applies, invoke it to check. If an
invoked skill turns out to be wrong for the situation, you don't have to use it.

```
user message received
  -> might any skill apply?
       yes (even a small chance) -> invoke the skill; follow it exactly
       definitely not           -> respond
```

### How to invoke a skill

Use the harness's skill-loading mechanism (the adapter maps this). Never read
skill files manually with file tools when a skill-loading mechanism exists — the
mechanism activates the skill properly.

### Instruction priority

1. **User's explicit instructions** (`AGENTS.md`, direct requests) — highest.
2. **Skills** — override default system behavior where they conflict.
3. **Default system prompt** — lowest.

If `AGENTS.md` says "don't use TDD" and the `tdd` skill says "always use TDD",
follow the user's instructions. The user is in control.

### When invoked as a subagent

If you were dispatched as a subagent to execute a specific task, skip the
skill-checking habit — your dispatcher already constructed your context. Focus on
the task.

## HABIT 2 — CHECK FOR PROJECT ARTIFACTS

After the skill check, check the project state:

1. **`CONTEXT.md` at repo root** — if it exists, read it for canonical terms. Use
   those terms throughout. If a term is fuzzy, invoke the `domain-modeling`
   discipline.
2. **Active plan folder** — resolve per `AGENTS.md §6`:
   - User named it: `build docs/plans/2026-06-28-fix-auth-timeout`.
   - Conversation context: the plan slug matches what the user is discussing.
   - Most-recently-modified plan folder, if still ambiguous.
   - Ask, if still ambiguous.
   If an active plan exists, read its artifacts (`PRD.md`, `ARD.md`, `SPEC.md`,
   `PLAN.md`, `LESSONS.md`, `RESEARCH.md`) before responding to plan-related work.

### The write habit

When something important happens, write it to the appropriate artifact:
- A new term is coined -> update `CONTEXT.md`.
- A requirement is clarified -> update `PRD.md` in the active plan.
- An invariant is discovered -> update `ARD.md` or `SPEC.md`.
- A bug is fixed -> append to `LESSONS.md`.

The artifacts are NOT memory — they are externalized state the agent maintains.
The habit of checking and updating them is what this skill teaches. (See
`AGENTS.md §10`.)

## ANNOUNCE

When you invoke a skill as a result of the habit, announce briefly: "Using the
`<skill>` skill to <purpose>." This keeps the user oriented without noise.

## BOUNDARIES

- MUST check for relevant skills before any response (even clarifying questions).
- MUST check for `CONTEXT.md` and an active plan folder.
- MUST use canonical terms from `CONTEXT.md`.
- MUST follow user instructions over skill defaults when they conflict.
- MUST NOT invoke skills when dispatched as a subagent for a specific task.
- MUST NOT write artifacts during the check — only read. Other skills write.
- MUST NOT be user-invoked or model-invoked. Only the adapter injects it.
