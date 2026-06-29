---
name: grill
description: |
  Sharpen a fuzzy idea into requirements before spec. Calibrated interrogation:
  one question at a time, recommend an answer, land each in PRD.md or CONTEXT.md.
  Creates the plan folder. The cheapest place to kill a bad idea is before a task
  exists.
  Use when the user has a vague idea, says "grill me", "stress-test this",
  "challenge my plan", "interview me", or before designing anything non-trivial.
invocation: user
layer: process
loop: grill
deliverable: new plan folder + PRD.md + updated CONTEXT.md
metadata:
  version: "1.0.0"
---

# grill — sharpen idea into PRD

One question at a time. Every answer lands in `PRD.md` or `CONTEXT.md`, or gets
parked as an explicit unknown. Never guess a requirement into existence.

Plan-then-execute guesses the fuzzy parts and builds the wrong thing. Grill drags
the fuzz into `PRD.md` *before* a single task exists. A bad assumption caught here
costs one question; caught in `LESSONS.md` it costs a bug.

## OWNERSHIP

Owns: the **plan folder** + `PRD.md` + `CONTEXT.md` glossary updates (may invoke
the `domain-modeling` discipline for the active glossary work).
Hands off to: `design` (→ `ARD.md`), or `spec` (→ `SPEC.md`) for right-sized work.
MUST NOT write `ARD.md`, `SPEC.md`, `PLAN.md`, or `LESSONS.md`.

## WHEN (user-invoked)

- Idea is one sentence and you can feel the holes.
- Multiple readings of the goal exist and you are about to pick one silently.
- Before `design` / `spec` on anything non-trivial.
- User asks to be challenged / stress-tested / grilled.

Skip for a typo or a one-line fix. Grill scales to uncertainty, not ego (§11).

## STEP 0 — READ EXISTING STATE

Before the first question:
1. Read `CONTEXT.md` at repo root if it exists — use its canonical terms.
2. Resolve the active plan per §6 (user names it, context matches slug,
   most-recently-modified, then ask). If none active, you will create one.
3. Read any existing `PRD.md` in the active plan to avoid re-asking settled points.

## STEP 1 — CREATE THE PLAN FOLDER

If no active plan, create one:
```
docs/plans/<yyyy-mm-dd>-<type>-<slug>/
```
- `yyyy-mm-dd` — today's date.
- `type` — `fix`, `feature`, `spike`, `refactor`, `chore`, `docs`, `test`.
- `slug` — short hyphenated description, from the user's own words.

Ask the user to confirm type + slug if ambiguous. Create the folder + an empty
`PRD.md` (written in step 4).

## STEP 2 — CALIBRATE FIRST

One opening read, not a quiz. Match the grilling to it:

1. How well does the user know this domain? (sets question depth)
2. How locked is the idea? (exploring vs committed)
3. Pressure wanted: light / normal / brutal.

Brutal grilling on a half-formed idea just demoralizes. Light grilling on a
committed plan misses the load-bearing flaw.

## STEP 3 — QUESTION LADDER

Climb in order. Each rung, ask **one** question, **recommend** an answer, wait.
Stop climbing the moment the PRD would be unambiguous — do not ask all seven by reflex.

1. **Goal** — what must the code *do*, in one line? (→ `PRD.md` § Goal)
2. **Done** — how do we know it works? name the observable. (→ `PRD.md` § Done)
3. **Boundary** — what is explicitly out of scope? (→ `PRD.md` § Out of scope)
4. **Lock** — what tech/lib/pattern is non-negotiable? what is forbidden? (→ `PRD.md` § Constraints)
5. **Surface** — what does the outside world touch — cmd, api, file, env? (→ `PRD.md` § Interfaces sketch)
6. **Edge** — the one input that breaks the happy path? (→ park as future invariant)
7. **Unknown** — what do we *not* know yet? (→ park as `?` in `PRD.md` § Open questions)

If a question can be answered by exploring the codebase, explore the codebase
instead of asking the user.

### Answer format

Each question carries a recommended answer so the user can grunt "yes" and move:

```
Q: auth — session cookie or JWT?
rec: JWT — stateless; you named horizontal scaling as a constraint.
(a) JWT  (b) cookie  (c) something else?
```

### Terminology

When a term is fuzzy or overloaded mid-interview, coin a canonical term and write
it to `CONTEXT.md` immediately (or invoke the `domain-modeling` discipline for the
active sharpening). Every name in the PRD MUST align with the glossary.

## STEP 4 — WRITE PRD.md

Write `PRD.md` in the plan folder using `caveman` compression. Template:

```markdown
# PRD — <slug>

## §G GOAL
<one line, what the code must do>

## §C CONSTRAINTS
- <non-negotiable boundary>
- <tech/lang/lib locked>
- <explicitly forbidden>

## §O OUT OF SCOPE
- <boundary>

## §I INTERFACES (sketch)
- <external surface: cmd / api / file / env>

## §D DONE
- <observable that proves it works>

## §V INVARIANTS (proposed, for ARD/SPEC)
- <rule that must hold>

## §Q OPEN QUESTIONS
- ? <blocking unknown>
```

Right-size: a one-line fix gets a minimal PRD (§G + §D only). A small feature gets
§G + §C + §D. Only genuinely uncertain or high-blast-radius work runs the full set.

## WHEN TO STOP

Done when ALL hold:
- §G is one line, one reading, zero "or maybe".
- §C covers every non-negotiable the user stated or implied.
- Every blocking unknown is either answered or parked as an explicit `?`.
- Every new term is in `CONTEXT.md`.

Unresolved blocking unknown that needs the outside world → recommend the
`research` loop, not a guess.

## HANDOFF

Emit a compact block — goal line, constraint bullets, surfaced unknowns as `?` —
and tell the user the next step:
- High-blast-radius or structurally uncertain → `design` (produces `ARD.md`).
- Straightforward but detailed → `spec` (produces `SPEC.md`).
- Already clear and small → `plan` (produces `PLAN.md`).

## BOUNDARIES

- MUST NOT make product decisions for the user. Recommend, never decide.
- MUST NOT write `ARD.md`, `SPEC.md`, `PLAN.md`, or `LESSONS.md`. Hand off.
- MUST NOT ask in bulk. One question, one recommendation, wait.
- MUST NOT grill a trivial change. Right-size or skip (§11).
- MUST read `CONTEXT.md` and use canonical terms throughout.
