---
name: research
description: |
  Gather external knowledge into the active plan's RESEARCH.md so build grounds in
  facts, not hallucinations. Every finding cites a source. Delegates to domain
  capabilities (e.g. research-literature for academic) based on their provides field.
  Use when the plan needs external facts before building, or when the user says
  "research this", "look up", "find docs on", "is there a library for".
invocation: user
layer: process
loop: research
deliverable: RESEARCH.md rows in the active plan (sourced, caveman)
metadata:
  version: "1.0.0"
---

# research — external knowledge into RESEARCH.md

Gather external knowledge the plan needs and distill it into `RESEARCH.md` — the
durable research log — so `build` grounds in facts instead of hallucinating
library behavior. Every finding cites a source; unsourced claims are flagged,
never written as fact.

Process without library context gives you well-organized hallucinations. `build`
invents a plausible-but-wrong API and `LESSONS.md` fills with avoidable bugs.
Research is the external oracle: pull the real fact once, log it in caveman, never
re-derive.

## OWNERSHIP

Owns: `RESEARCH.md` in the active plan folder (appends sourced rows).
Reads: `PRD.md`, `ARD.md`, `SPEC.md`, `CONTEXT.md`.
Hands off to: `spec` (if a finding changes a `§C` constraint or `§I` interface,
note the edit for `spec` to make).
MUST NOT write `PRD.md`, `ARD.md`, `SPEC.md`, `PLAN.md`, or `LESSONS.md`.

## WHEN (user-invoked)

- A constraint / interface / invariant decision hinges on a library, API,
  version, or pattern you are unsure of.
- You are about to assume how an external dependency behaves.
- The idea touches a domain with real prior art (auth, payments, crypto,
  rate-limiting, distributed systems).
- `grill` parked a `?` that the outside world must answer.
- User says "research this", "look up", "find docs on", "is there a library for".

Skip when the build touches only code you already wrote. Research scales to the
unknown, not to habit.

## STEP 0 — READ EXISTING STATE

1. Resolve the active plan per §6. If none, ask the user to run `grill` first
   (research needs a question in scope).
2. Read `PRD.md` to find parked `?` items and the constraints/interfaces the
   research must inform.
3. Read `CONTEXT.md` for canonical terms.

## STEP 1 — SCOPE

Turn the unknown into 1-3 concrete questions. Vague "research auth" becomes:
"JWT lib for Node ESM, maintained?" + "refresh-token rotation: current best
practice?". A scoped question gets a citable answer; a vague one gets an essay.

## STEP 2 — DELEGATE TO DOMAIN CAPABILITIES

If the question falls in a domain a capability skill covers, delegate to it (by
the `provides:` field in the domain skill's frontmatter, per §5):

- Academic / literature search -> the `research-literature` skill
  (`provides: [academic-search]`).
- Other domain capabilities as they are added.

If no domain capability fits, gather directly using web search / docs tools.

Prefer primary sources: official docs, the repo, the RFC, the paper. Two
independent sources beat one confident blog. For a big sweep, dispatch a subagent
(via the `dispatch` discipline) so the raw pages never touch this context — it
returns only the distilled finding + source.

## STEP 3 — DISTILL

Crush each answer to one caveman line + its source. Drop the prose. The `RESEARCH.md`
row is the memory; the tab you read is not.

```
R3|refresh token|rotate on use, revoke family on reuse-detect|datatracker.ietf.org/doc/html/rfc6819#section-5.2.2.3
```

## STEP 4 — WRITE RESEARCH.md + HAND OFF

Append the `§R` rows to `RESEARCH.md` using caveman. If a finding changes a
constraint or interface, note the `§C`/`§I` edit for the `spec` skill to make.
Research proposes; `spec` writes.

Template for `RESEARCH.md`:

```markdown
# RESEARCH — <slug>

## §R FINDINGS

id|topic|finding|source
R1|jwt lib|`jose` > `jsonwebtoken` — maintained, ESM, 0 deps|github.com/panva/jose
R2|rate limit|token bucket ok @ our scale|<url>
R3|refresh token|rotate on use, revoke family on reuse-detect|datatracker.ietf.org/doc/html/rfc6819#section-5.2.2.3
```

Table cell rules: literal `|` -> escape as `\|`. Empty = `-`.

## SOURCE DISCIPLINE

- Cite a URL, repo, RFC, or paper per row. Verbatim identifiers / versions.
- Could not verify -> write the row but flag `?` in the finding and say so. An
  unverified claim labeled honestly is fine; one disguised as fact is a future
  `LESSONS.md` bug.
- Conflicting sources -> log both, let the user pick. NEVER silently average them.

## WHEN TO STOP

Done when every scoped question has a sourced `§R` row (or an honest `?`), and no
build decision still rests on an unchecked assumption. Do not research past the
questions you scoped — that is just burning the attention budget.

## BOUNDARIES

- MUST NOT write `SPEC.md` / `PRD.md` / `ARD.md` / `PLAN.md` / `LESSONS.md`. Hand
  `§R` rows + any `§C`/`§I` edit notes to `spec`.
- MUST NOT write a finding as fact without a source.
- MUST NOT dump raw pages into context or `RESEARCH.md`. Distill or it does not land.
- MUST NOT research what you can read in the repo. Local truth > web guess.
- MUST delegate to domain capabilities by their `provides` field when one fits.
- MUST use `caveman` and `CONTEXT.md` canonical terms.
