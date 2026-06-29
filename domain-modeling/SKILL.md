---
name: domain-modeling
description: |
  Actively build and sharpen a project's ubiquitous language. Challenge terms
  against the glossary, stress-test with edge-case scenarios, update CONTEXT.md
  inline the moment a term crystallizes, offer ADRs for hard decisions.
  Use when terminology is fuzzy, overloaded, or conflicts with the glossary, or
  when the user says "what do we call this", "define this", or asks about
  ubiquitous language.
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# domain-modeling — sharpen the ubiquitous language

Actively build and sharpen the project's ubiquitous language as you work. This is
the *active* discipline — challenging terms, inventing edge-case scenarios, and
writing the glossary and decisions down the moment they crystallize.

Merely *reading* `CONTEXT.md` for vocabulary is a one-line habit any skill can do.
This skill is for when you are *changing* the model, not just consuming it.

## OWNERSHIP

Owns: `CONTEXT.md` at the repo root (the glossary) + offers ADRs in
`docs/adr/` when a decision is hard to reverse.
Reads: the codebase, `CONTEXT.md`, the active plan's artifacts.
MUST NOT write plan artifacts (`PRD.md`/`ARD.md`/`SPEC.md`/`PLAN.md`/`LESSONS.md`).
Invoked by: `grill`, `design`, `spec`, `build` (any skill that coins or sharpens a
term).

## WHEN (self-trigger)

- Terminology is fuzzy, overloaded, or conflicts with the glossary.
- A new concept is named and not yet in `CONTEXT.md`.
- The user asks "what do we call this", "define this", "is that the same as X?".
- Another skill coins a term and delegates the glossary update here.

## FILE STRUCTURE

Most repos have a single context:

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts. The map
points to where each one lives:

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          <- system-wide decisions
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  <- context-specific decisions
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

Create files lazily — only when you have something to write. If no `CONTEXT.md`
exists, create one when the first term is resolved. If no `docs/adr/` exists,
create it when the first ADR is needed.

## DURING THE SESSION

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in
`CONTEXT.md`, call it out immediately: "Your glossary defines 'cancellation' as X,
but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term:
"You're saying 'account' — do you mean the Customer or the User? Those are
different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific
scenarios. Invent scenarios that probe edge cases and force the user to be
precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you
find a contradiction, surface it: "Your code cancels entire Orders, but you just
said partial cancellation is possible — which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Do not batch these up —
capture them as they happen.

`CONTEXT.md` should be totally devoid of implementation details. Do not treat it
as a spec, a scratch pad, or a repository for implementation decisions. It is a
glossary and nothing else.

#### CONTEXT.md format

Each entry has a canonical term and a list of synonyms to avoid:

```markdown
## materialization cascade

When a lesson inside a section of a course is made real (given a spot in the file system).

_Evitar_: "lesson becomes real", "section activation", "file system placement"
```

### Offer ADRs sparingly

Only offer to create an ADR when ALL THREE are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful.
2. **Surprising without context** — a future reader will wonder "why did they do
   it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you
   picked one for specific reasons.

If any of the three is missing, skip the ADR. ADRs live in `docs/adr/` and are
numbered: `0001-<slug>.md`, `0002-<slug>.md`, ...

#### ADR format

```markdown
# ADR 0001: <decision title>

## Status
Accepted (2026-06-28)

## Context
<why this decision is being made — the forces at play>

## Decision
<what we decided>

## Consequences
<what this makes easy, what this makes hard>

## Alternatives considered
- <alt A>: <trade-off>
- <alt B>: <trade-off>
```

## WHEN TO STOP

Done when:
- Every term used in the active plan's artifacts has a canonical entry in
  `CONTEXT.md` (or a `?` flag pending resolution).
- Every fuzzy term the user raised has been sharpened to a canonical term.
- Every hard-to-reverse decision with real alternatives has an ADR offered (and
  written if the user agreed).

## BOUNDARIES

- MUST update `CONTEXT.md` inline the moment a term crystallizes (no batching).
- MUST keep `CONTEXT.md` a pure glossary — no implementation details.
- MUST NOT write plan artifacts. Coin terms here; the invoking skill writes them
  into its artifact.
- MUST offer ADRs sparingly — only when all three criteria hold.
- MUST challenge terms against the glossary and cross-reference with the code.
