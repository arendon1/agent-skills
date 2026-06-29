---
name: review
description: |
  Adversarial senior review of the plan before build, or of the code after build.
  Constructs a skeptical reviewer anchored to the codebase, RESEARCH.md, and live
  best-practice, then tries to REFUTE — not rubber-stamp. Every finding cites
  evidence. Ends in a go/no-go gate.
  Use when reviewing high-blast-radius work before build, or reviewing the diff
  after build, or when the user says "review the spec", "red-team this", "is this
  sound", "senior review".
invocation: user
layer: process
loop: review
deliverable: review report (design or code) with a go/no-go gate
metadata:
  version: "1.0.0"
---

# review — refute, do not rubber-stamp

Adversarial senior review. Two modes: **design review** (before build, on the
plan artifacts) and **code review** (after build, on the diff). Constructs a
skeptical reviewer whose authority comes from the codebase, `RESEARCH.md`, and
live best-practice — then tries to REFUTE the work, not rubber-stamp it. Every
finding cites evidence (file:line or source); unverifiable ones are flagged. Ends
in an explicit go / no-go gate.

An LLM cannot self-correct on its own judgment — left alone it drifts. Review
fixes that the only way that works: a separate skeptic anchored to an external
oracle.

## OWNERSHIP

Owns: the review report (delivered inline + may be saved to the plan folder as
`REVIEW.md` if the user wants it persisted).
Reads: `PRD.md`, `ARD.md`, `SPEC.md`, `PLAN.md`, `RESEARCH.md`, `CONTEXT.md`,
the codebase (and the diff, in code-review mode).
MUST NOT rewrite any artifact. MAY draft `§V` invariants for the `spec` skill to
write. MAY propose remediations for `build` to apply.

## WHEN (user-invoked)

### Design review (before build)
- Before `build` on a high-blast-radius change (shared module, auth, data,
  money, public interface).
- The plan touched interfaces or invariants other code depends on.
- Right-sizing says the cost of a wrong build > the cost of one review pass.

### Code review (after build)
- After `build` completes a task or a plan, on the diff.
- Before merge / PR.

Skip for a trivial, reversible, well-understood change. Adversarial review on a
typo hallucinates flaws and wastes the budget — the self-critique paradox is real.

## PHASE 0 — CAPTURE

Design review: read the plan artifacts (`PRD.md` `ARD.md` `SPEC.md` `PLAN.md`
`RESEARCH.md`). Hold the whole thing. Review the *artifacts*, not your memory of
the conversation.

Code review: read the diff (staged or the branch's commits). Review the *changes*,
not the whole codebase.

## PHASE 1 — CONSTRUCT THE SENIOR

Build a reviewer with real authority, not a generic critic:
- **Codebase** — grep/read the modules this work touches. What patterns, what
  invariants already hold?
- **RESEARCH.md** — what did research establish? A decision that contradicts
  `RESEARCH.md` is a finding.
- **Live** — for any best-practice claim you are unsure of, fetch it. An
  out-of-date assumption is a flaw.

A reviewer with no evidence is just an opinion. Earn the authority first.

## PHASE 2 — REFUTE

### Design review axes
- **Goal vs reality** — does the PRD solve the actual problem, or a proxy?
- **Missing invariant** — what can go wrong that no `§V` catches? (most findings)
- **Interface drift** — does `§I` match what callers already expect? (cite the
  caller, file:line)
- **Constraint conflict** — do two `§C` bullets contradict? does one fight
  `RESEARCH.md`?
- **Unowned edge** — the input, ordering, failure, or concurrency case no task
  covers.
- **Altitude** — tasks too vague to act on, or so granular they are just typing?

### Code review axes
- **Spec compliance** — does the code do what `SPEC.md` `§V`/`§I` say?
- **Regression** — does the change break an existing invariant or test?
- **Behavior preservation** — does a refactor actually preserve behavior?
- **Test quality** — do the new tests verify behavior (good) or implementation
  (bad)? Are there tests for the cited invariants?
- **Hidden coupling** — does the change introduce coupling the spec doesn't name?
- **Error handling** — are failure modes covered or papered over?

## PHASE 3 — CLASSIFY

Each finding: `evidence -> claim -> severity`.

- **BLOCK** — shipping this ships a real defect. Must fix first.
- **HARDEN** — add/sharpen a `§V` so the build cannot regress it.
- **NOTE** — worth knowing, not blocking.

No evidence? Down-rank to NOTE and tag `[unverified]`. NEVER inflate a hunch to
BLOCK.

## PHASE 4 — HARDEN §V + GATE

- Each HARDEN finding -> a draft `§V` line (testable, cites the interface and
  the behavior it guards). Hand to the `spec` skill to write (design review) or the `lessons`
  reflex (code review, post-fix).
- End on an explicit gate (caveman):

```
## review verdict
BLOCK: 1 — §I.api shape != caller src/client.ts:40. fix §I before build.
HARDEN: 2 — drafted V8 (idempotent refund), V9 (tx around dual write).
NOTE: 1 — T4 vague, split before build.
gate: NO-GO until BLOCK cleared. then build §T after spec writes V8,V9.
```

GO or NO-GO, never a shrug. Review is the checkpoint that stops a confident wrong
build.

## BOUNDARIES

- MUST NOT rewrite any artifact. Draft `§V` and hand to `spec` / `lessons`.
- MUST cite evidence (file:line or source) for every finding.
- MUST flag unverifiable findings as `[unverified]`, never pass them as fact.
- MUST end on GO or NO-GO. Never a shrug.
- MUST NOT review trivia. Right-size or skip (§11).
- MUST NOT rewrite the user's intent. Harden the work; do not replace its goal.
- MUST use `caveman` for the verdict block and `CONTEXT.md` canonical terms.
