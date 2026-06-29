---
name: design
description: |
  Architecture design pass. Turn a PRD into an ARD: components, interfaces,
  invariants, data flow, error handling. Propose 2-3 structural approaches with
  trade-offs. Recommend one. Behavior preserved.
  Use when the objective is non-trivial or high-blast-radius, after grill and
  before spec, or when the user says "design this", "architecture", "how should we
  structure this".
invocation: user
layer: process
loop: design
deliverable: ARD.md in the active plan folder
metadata:
  version: "1.0.0"
---

# design — PRD into ARD

Architecture design pass. Reads `PRD.md`, proposes 2-3 structural approaches,
recommends one, lands the choice in `ARD.md` as components, interfaces,
invariants, data flow, and error handling.

A design pass is for non-trivial or high-blast-radius work. For a one-line fix or
a small obvious feature, skip straight to `spec` or `plan` (§11 right-size).

## OWNERSHIP

Owns: `ARD.md` in the active plan folder.
Reads: `PRD.md` (from `grill`), `CONTEXT.md`, the codebase.
Hands off to: `spec` (→ `SPEC.md`).
MUST NOT write `PRD.md`, `SPEC.md`, `PLAN.md`, or `LESSONS.md`.
MAY propose new `CONTEXT.md` terms (via the `domain-modeling` discipline).

## WHEN (user-invoked)

- After `grill` produced a `PRD.md`, on non-trivial or high-blast-radius work.
- User says "design this", "architecture", "how should we structure this".
- The PRD names a structural decision that has more than one viable answer.

## STEP 0 — READ EXISTING STATE

1. Resolve the active plan per §6. If none, ask the user to run `grill` first
   (design needs a PRD to design from).
2. Read `PRD.md`. If absent, stop and recommend `grill`.
3. Read `CONTEXT.md` — use canonical terms throughout the ARD.
4. Read the relevant code: what exists, what seams already exist, what ADRs hold.

## STEP 1 — FRAME THE DESIGN DECISIONS

From the PRD, extract the load-bearing design decisions — the ones with more than
one viable answer. Examples: where the state lives, what is sync vs async, what
owns a transaction boundary, where validation happens, what is a process vs a
library. These are the decisions the ARD must resolve.

State each decision in one line. A decision the PRD already locked is not a
design decision — it is a constraint.

## STEP 2 — PROPOSE 2-3 STRUCTURAL APPROACHES

For each load-bearing decision, draft 2-3 approaches. Each approach names:
- **Structure** — the components and their boundaries.
- **Trade-off** — what this makes easy, what this makes hard.
- **Cost** — blast radius, new dependencies, migration effort.
- **Risk** — what could be wrong about this.

Favor approaches that reuse existing seams over inventing new ones. The fewer
seams across the codebase, the better — the ideal number is one.

## STEP 3 — RECOMMEND ONE

Pick one approach per decision and justify it against the PRD's constraints and
the trade-offs. Be willing to say "approach B is safer because the PRD's
out-of-scope already forecloses approach A's main benefit."

Present the recommendation to the user. Wait for agreement before writing the ARD.

## STEP 4 — WRITE ARD.md

Write `ARD.md` using `caveman` compression. Template:

```markdown
# ARD — <slug>

## §D DECISIONS
D1: <decision> -> <chosen approach>
  - alt: <approach B> (trade-off)
  - rec: <why this one>

## §C COMPONENTS
- <component>: <responsibility> (deep module: small interface, hides a decision)

## §I INTERFACES
api: POST /x -> 200 {id}
cmd: `foo bar <arg>` -> stdout JSON
env: FOO_KEY MUST be set

## §V INVARIANTS
V1: MUST <testable rule>
V2: <condition> => <outcome>

## §F DATA FLOW
<one paragraph or ascii diagram: input -> component -> store -> output>

## §E ERROR HANDLING
- <failure mode> -> <recovery>
- NEVER <forbidden recovery>

## §R RISKS
- <risk> SHOULD <mitigation>
```

### Deep-module vocabulary

Borrow from the `deepen` discipline's vocabulary when describing components. A
**deep module** hides a lot behind a small interface; a **shallow** one's
interface costs as much to use as writing the code yourself. Note any component
that risks shallowness as a `§R` risk so `deepen` can address it later.

### Terminology

Every new component/interface name goes into `CONTEXT.md` immediately (or invoke
the `domain-modeling` discipline). ARD terms MUST match the glossary.

## WHEN TO STOP

Done when:
- Every load-bearing decision from step 1 has a chosen approach + justification.
- Components, interfaces, invariants, data flow, and error handling are written.
- The user agreed to the recommendation.
- New terms are in `CONTEXT.md`.

## HANDOFF

Tell the user the next step:
- Detailed behavior needed before tasks → `spec` (produces `SPEC.md`).
- The ARD is detailed enough → `plan` (produces `PLAN.md`).

## BOUNDARIES

- MUST NOT rewrite `PRD.md`. If requirements are wrong, route back to `grill`.
- MUST NOT write `SPEC.md`, `PLAN.md`, or `LESSONS.md`.
- MUST propose alternatives before recommending — no single-option "design".
- MUST read `CONTEXT.md` and use canonical terms throughout.
- MUST NOT change behavior. Design proposes structure; `build` implements.
