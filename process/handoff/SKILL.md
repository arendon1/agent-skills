---
name: handoff
description: |
  Compact the current session into a handoff document so another agent (or a fresh
  session) can continue the work. Captures goal, state, decisions, next steps, and
  pointers to artifacts. Does not duplicate content already in artifacts.
  Use when ending a session mid-plan, or when handing work to another agent, or
  when the user says "handoff", "compact this", "I'm leaving", "pass this to
  another agent", "save state for later", "wrap up".
invocation: user
layer: process
loop: handoff
deliverable: handoff document (saved to the OS temp dir, not the workspace)
metadata:
  version: "1.0.0"
---

# handoff — compact the session

Compact the current conversation into a handoff document so a fresh agent can
continue the work. Captures goal, state, decisions, next steps, and pointers to
artifacts — without duplicating content already captured in plan artifacts,
commits, diffs, or ADRs.

## OWNERSHIP

Owns: the handoff document (saved to the OS temp dir, NOT the workspace).
Reads: the active plan's artifacts (`PRD.md`, `ARD.md`, `SPEC.md`, `PLAN.md`,
`LESSONS.md`, `RESEARCH.md`), `CONTEXT.md`, git state.
MUST NOT write plan artifacts. References them by path, never duplicates them.

## WHEN (user-invoked)

- Ending a session mid-plan.
- Handing work to another agent.
- User says "handoff", "compact this", "I'm leaving", "pass this to another
  agent", "save state for later", "wrap up".
- Before a compaction resets context (if invoked manually rather than by the
  adapter).

## STEP 0 — CAPTURE THE ARGUMENT

If the user passed an argument, treat it as a description of what the next
session will focus on and tailor the handoff to it. Otherwise, capture the whole
current state.

## STEP 1 — GATHER STATE

1. Resolve the active plan per §6. Note its path.
2. Read the active plan's artifacts. Note their paths + a one-line summary of
   each (do NOT duplicate their content).
3. Read `CONTEXT.md`. Note its path.
4. Check git state: current branch, uncommitted changes, recent commits.
5. Note any `?` items, in-progress tasks (`~`), and blocking unknowns.

## STEP 2 — WRITE THE HANDOFF

Save to the OS temp directory (not the workspace — it is a scratch doc, not a
versioned artifact). Use `caveman`-light (compressed but readable).

Template:

```markdown
# HANDOFF — <objective>

> For a fresh agent picking up <objective>. Read this, then open the plan artifacts.

## goal
<one line: what the work is>

## current state
- active plan: docs/plans/<date>-<type>-<slug>/
- branch: <branch>, <clean|uncommitted: N files>
- artifacts: <list paths + one-line summary each, NOT content>

## decisions made
- <decision 1> (in ARD.md §D / ADR 000N)
- <decision 2>

## next steps
1. <next step 1 — e.g. "run build on §T.4">
2. <next step 2>
3. <open question parked as ? — needs research>

## pointers
- plan artifacts: docs/plans/<slug>/
- CONTEXT.md: ./CONTEXT.md
- recent commits: <commit hashes + subjects>

## suggested skills
- <skill 1> — <why>
- <skill 2> — <why>

## redacted
- (any sensitive info redacted — API keys, passwords, PII)
```

## SOURCE DISCIPLINE

- DO NOT duplicate content already captured in artifacts (PRDs, plans, ADRs,
  issues, commits, diffs). Reference them by path or URL instead.
- Redact any sensitive information: API keys, passwords, personally identifiable
  information. If you must reference that a secret exists, say "secret configured
  in env var FOO_KEY" without the value.

## SUGGESTED SKILLS

Include a "suggested skills" section that names the skills the next agent should
invoke, with a one-line reason each. Examples:

```
## suggested skills
- bootstrap — re-enable auto-triggering + artifact-check habit at session start
- build — execute §T.4 next (status ~, blocked by §T.3 which is [x])
- verify — gate §T.4 before flipping to [x]
- lessons — if §T.4's test fails, trace root cause
```

## BOUNDARIES

- MUST save to the OS temp dir, NOT the workspace.
- MUST NOT duplicate content already in artifacts. Reference by path.
- MUST redact sensitive information.
- MUST include a "suggested skills" section.
- MUST use canonical terms from `CONTEXT.md`.
- MUST NOT write plan artifacts.
