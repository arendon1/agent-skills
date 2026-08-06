---
name: review
description: |
  Adversarial senior review of the plan before build, or of the code after build.
  Constructs a skeptical reviewer anchored to the codebase, RESEARCH.md, and live
  best-practice, then tries to REFUTE — not rubber-stamp. Every finding cites
  evidence. Code review runs two axes (Standards + Spec) as parallel isolated
  reviewers, reported side by side. Ends in a go/no-go gate.
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
Code review builds TWO seniors (see PHASE 2) so the axes never pollute each
other's context.

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

### Code review: two axes, two isolated reviewers

A change can pass one axis and fail the other:

- Code that follows every standard but implements the wrong thing →
  **Standards pass, Spec fail**.
- Code that does exactly what the issue asked but breaks conventions →
  **Spec pass, Standards fail**.

Reporting them separately stops one axis from masking the other. Run BOTH axes
as parallel isolated reviewers (separate contexts, no cross-pollution), then
aggregate their reports side by side. NEVER merge or rerank findings across axes.

**Standards axis** — does the diff follow this repo's documented standards?
Sources: anything documenting how code should be written (`CODING_STANDARDS.md`,
`CONTRIBUTING.md`). On top of documented standards, always carry the **smell
baseline** below. Rules: a documented repo standard always overrides the
baseline; each baseline smell is a labelled heuristic, never a hard violation;
skip anything tooling already enforces.

**Spec axis** — does the diff faithfully implement the originating spec?
Sources, in order: issue/ticket references in commit messages; the path the user
passed; a spec file under `docs/`, `specs/`, or the active plan folder; else
ask. If no spec exists, the Spec axis reports "no spec available" and skips.

Report format (per axis, verbatim — do not merge):

- **Standards** — per file/hunk: (a) documented-standard violations: cite the
  standard (file + rule); (b) baseline smells: name it and quote the hunk.
  Distinguish hard violations from judgement calls.
- **Spec** — (a) requirements asked but missing or partial; (b) behaviour in the
  diff not asked for (scope creep); (c) requirements that look implemented but
  wrong. Quote the spec line per finding.

### Smell baseline (Fowler, ch.3 — applies even when the repo documents nothing)

| smell | reads as | fix |
|-------|----------|-----|
| Mysterious Name | name does not reveal what it does or holds | rename; no honest name = murky design |
| Duplicated Code | same logic shape in > 1 hunk or file | extract shared shape, call from both |
| Feature Envy | method reaches into another object's data more than its own | move method onto the data it envies |
| Data Clumps | same few fields/params keep travelling together | bundle into one type, pass that |
| Primitive Obsession | primitive/string standing in for a domain concept | give the concept its own small type |
| Repeated Switches | same switch/if-cascade on same type recurs | polymorphism, or one map both sites share |
| Shotgun Surgery | one logical change scatters edits across files | gather what changes together into one module |
| Divergent Change | one file edited for several unrelated reasons | split so each module changes for one reason |
| Speculative Generality | abstraction/hooks added for needs the spec lacks | delete; inline back until a real need shows |
| Message Chains | long `a.b().c().d()` navigation callers depend on | hide the walk behind one method |
| Middle Man | class/function mostly just delegates onward | cut it, call the real target direct |
| Refused Bequest | subclass ignores or overrides most inherited behaviour | drop inheritance, use composition |

## PHASE 3 — CLASSIFY

Each finding (from either axis, in code review): `evidence -> claim -> severity`.

- **BLOCK** — shipping this ships a real defect. Must fix first.
- **HARDEN** — add/sharpen a `§V` so the build cannot regress it.
- **NOTE** — worth knowing, not blocking.

No evidence? Down-rank to NOTE and tag `[unverified]`. NEVER inflate a hunch to
BLOCK.

## PHASE 4 — HARDEN §V + GATE

- Each HARDEN finding -> a draft `§V` line (testable, cites the interface and
  the behavior it guards). Hand to the `spec` skill to write (design review) or the `lessons`
  reflex (code review, post-fix).
- End on an explicit gate (caveman). In code review, state the worst issue per
  axis and gate on the aggregate:

```
## review verdict
Standards: 1 BLOCK (middle man in api.ts:40) — fix before merge.
Spec: 2 HARDEN — drafted V8 (idempotent refund), V9 (tx around dual write).
gate: NO-GO until BLOCK cleared. then build §T after spec writes V8,V9.
```

GO or NO-GO, never a shrug. Review is the checkpoint that stops a confident wrong
build.

## BOUNDARIES

- MUST NOT rewrite any artifact. Draft `§V` and hand to `spec` / `lessons`.
- MUST cite evidence (file:line or source) for every finding.
- MUST flag unverifiable findings as `[unverified]`, never pass them as fact.
- MUST run code-review axes as parallel isolated reviewers; MUST NOT merge or
  rerank findings across axes.
- MUST end on GO or NO-GO. Never a shrug.
- MUST NOT review trivia. Right-size or skip (§11).
- MUST NOT rewrite the user's intent. Harden the work; do not replace its goal.
- MUST use `caveman` for the verdict block and `CONTEXT.md` canonical terms.
