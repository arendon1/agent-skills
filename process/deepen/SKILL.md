---
name: deepen
description: |
  Make one shallow module deeper — move complexity behind a smaller interface,
  held at a clean seam, testable through that interface. Behavior preserved, tests
  green before and after. Proposes §I/§V/§T edits, never silent rewrites.
  Use when a module is shallow (big surface, little behavior), or when spare
  budget exists for a design pass, or when the user says "refactor this", "this is
  messy", "deepen", "improve this module".
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# deepen — make one module deeper

Behavior is sacred: tests green before AND after. Every change shrinks an
interface or hides a decision — deepen, don't churn.

A **deep module** hides a lot behind a small interface; a **shallow** one's
interface costs as much to use as writing the code yourself. Complexity =
dependencies + obscurity, and it compounds. `deepen` spends spare budget paying
that down *before* it becomes a `LESSONS.md` bug. Run it when the build is green
and you have budget to drain — not under deadline.

## OWNERSHIP

Owns: proposed `§I`/`§V`/`§T` amendments for the chosen module (handed to `spec`
to write).
Reads: `SPEC.md`, `ARD.md`, `CONTEXT.md`, the codebase.
MUST NOT silently rewrite code or artifacts. Proposes via `spec`; `build` applies.

## WHEN (self-trigger)

- Build is green, tests pass, and you have token budget spare.
- A module's interface feels as complex as its implementation (shallow smell).
- The same change keeps touching many files (change amplification).
- A `?` or `LESSONS.md` bug traces back to a confusing interface.
- User says "deepen this", "refactor this", "this module is shallow", "improve
  the design", "pull complexity down", "spare-budget design".

NEVER run mid-feature or under pressure. `deepen` is the deliberate pass, not the
reflex.

## THE FIVE STEPS

### 1. Pick the shallow

Scan the modules the active plan touches. Rank by shallowness — interface surface
vs work done. Pick the **one** worst offender. Tells:

- Pass-through method that only forwards to one other (shallow layer).
- Caller must set 5 flags right to use it (config leakage).
- Same abstraction repeated at two layers (no information hiding).
- A `?` or `LESSONS.md` bug that traces back to a confusing interface.

One module per pass. Deepening is surgical, not a codebase sweep.

### 2. Diagnose

Name the design defect in caveman, citing file:line:

```
src/auth/token.go: 6-arg ctor leaks rotation policy to every caller. shallow.
```

Complexity is real only if it shows: change amplification, high cognitive load, or
an unknown-unknown (caller must know a hidden fact to call it right).

### 3. Research the deepening

What does a deeper version look like? Pull a known pattern (hand to the `research`
loop for the external case -> `RESEARCH.md`) or derive from the codebase's own
better modules. Moves that deepen:

- **Pull complexity down** — hide the hard part inside, give callers the simple path.
- **Define errors out of existence** — design the interface so the edge can't occur.
- **Information hiding** — one decision, one module; callers don't learn it.
- **General-purpose interface** over a pile of special-case methods.

### 4. Propose

Draft the change as spec edits, not a silent rewrite:
- New/simpler `§I` shape for the module.
- `§V` that locks the deepened invariant so a future build can't re-shallow it.
- `§T` refactor row(s), each citing the `§V`/`§I` it serves.

Hand to the `spec` skill to write. Show the before/after interface so the user
sees the shrink.

### 5. Verify behavior held

Refactor != rewrite. Full suite green before you start AND after. A deepening
that changes behavior is a feature in disguise — stop, route through `spec` +
`build`. New interface gets a test proving the old callers still work.

## WHEN TO STOP

Done when the chosen module's interface is strictly smaller, its hidden decision
no longer leaks, tests are green, and `§I`/`§V` record the new shape. One module
deepened beats five churned. Budget left -> pick the next shallowst, fresh pass.

## BOUNDARIES

- MUST NOT change behavior. Green before, green after. Pure structure.
- MUST NOT silently rewrite code or artifacts. Propose `§I`/`§V`/`§T` via `spec`.
- MUST pick ONE module per pass. Surgical, not a sweep.
- MUST cite file:line for the diagnosed defect.
- MUST use `caveman` and `CONTEXT.md` canonical terms.
- MUST NOT run mid-feature or under pressure.
