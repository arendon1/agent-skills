---
name: prototype
description: |
  Build a throwaway prototype to flesh out a design — a runnable terminal app for
  state/business-logic questions, or several radically different UI variations
  toggleable from one route. Cheap exploration before committing to a spec.
  Use when a design question is cheaper answered by building than by talking, or
  when the user says "prototype", "spike", "let's try it", "build a throwaway",
  "explore this design", "proof of concept", "POC".
invocation: user
layer: process
loop: prototype
deliverable: throwaway prototype / UI variants + a captured answer (ADR/commit/NOTES.md)
metadata:
  version: "1.0.0"
---

# prototype — throwaway exploration

A prototype is **throwaway code that answers a question**. The question decides
the shape. Cheap exploration before committing to a spec.

## OWNERSHIP

Owns: the throwaway prototype code + a captured answer (commit message, ADR, or
`NOTES.md` next to the prototype).
Reads: `CONTEXT.md`, the relevant code.
Hands off to: `grill` / `design` / `spec` with the captured answer, if the answer
informs a real plan.
MUST NOT write plan artifacts. A prototype is *pre*-plan; if a plan exists, route
through `spec` instead.

## WHEN (user-invoked)

- A design question is cheaper answered by building than by talking.
- User says "prototype", "spike", "let's try it", "build a throwaway", "explore
  this design", "proof of concept", "POC".
- The state model has too many moving parts to reason about on paper.
- The UI has multiple radically different viable directions.

Skip when the design is already clear — a prototype then is wasted budget.

## STEP 0 — PICK A BRANCH

Identify which question is being answered — from the user's prompt, the
surrounding code, or by asking if the user is around:

- **"Does this logic / state model feel right?"** -> **logic branch**. Build a tiny
  interactive terminal app that pushes the state machine through cases that are
  hard to reason about on paper.
- **"What should this look like?"** -> **UI branch**. Generate several radically
  different UI variations on a single route, switchable via a URL search param and
  a floating bottom bar.

The two branches produce very different artifacts — getting this wrong wastes the
whole prototype. If the question is genuinely ambiguous and the user isn't
reachable, default to whichever branch better matches the surrounding code (a
backend module -> logic; a page or component -> UI) and state the assumption at
the top of the prototype.

## RULES (both branches)

1. **Throwaway from day one, clearly marked.** Locate the prototype code close to
   where it will actually be used (next to the module or page it's prototyping
   for) so context is obvious — but name it so a casual reader can see it's a
   prototype, not production. For throwaway UI routes, obey whatever routing
   convention the project already uses; don't invent a new top-level structure.
2. **One command to run.** Whatever the project's existing task runner supports.
   The user must be able to start it without thinking.
3. **No persistence by default.** State lives in memory. Persistence is the thing
   the prototype is *checking*, not something it should depend on. If the question
   explicitly involves a database, hit a scratch DB or a local file with a clear
   "PROTOTYPE — wipe me" name.
4. **Skip the polish.** No tests, no error handling beyond what makes the
   prototype *runnable*, no abstractions. The point is to learn something fast and
   then delete it.
5. **Surface the state.** After every action (logic) or on every variant switch
   (UI), print or render the full relevant state so the user can see what changed.
6. **Delete or absorb when done.** When the prototype has answered its question,
   either delete it or fold the validated decision into the real code — don't
   leave it rotting in the repo.

## WHEN DONE

The *answer* is the only thing worth keeping from a prototype. Capture it
somewhere durable (commit message, ADR, or a `NOTES.md` next to the prototype)
along with the question it was answering. If the user is around, that capture is
a quick conversation; if not, leave the placeholder so they (or you, on the next
pass) can fill in the verdict before deleting the prototype.

### Handoff

If the answer informs a real objective, hand to:
- `grill` — if the prototype revealed requirements that need sharpening.
- `design` — if the prototype revealed a structural decision.
- `spec` — if the prototype produced a snippet that encodes a decision (state
  machine, reducer, schema, type shape) more precisely than prose. Trim to the
  decision-rich parts — not a working demo, just the important bits.

## BOUNDARIES

- MUST mark the prototype as throwaway from day one.
- MUST NOT add tests, error handling, or abstractions beyond runnable.
- MUST NOT persist by default (in-memory; scratch DB only if the question needs it).
- MUST capture the answer before deleting the prototype.
- MUST delete or absorb the prototype when the question is answered.
- MUST use `CONTEXT.md` canonical terms in any captured answer.
