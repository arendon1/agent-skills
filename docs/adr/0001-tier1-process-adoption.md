# ADR-0001 — Tier-1 process-layer adoption (mattpocock/skills margins)

Status: accepted
Date: 2026-08-05
Source: plan `2026-08-05-refactor-process-tier1`

## Decision

Adopt 5 mechanics from `mattpocock/skills` into the process layer, keeping
`skill-forge audit` as the constitution enforcer:

1. **`grilling` primitive** — interview engine (design tree, frontier rounds,
   facts-are-the-agent's-job, non-blocking helper dispatch). `grill` (user
   loop) runs it; grilling owns no artifacts.
2. **Two-axis code review** — Standards + Spec as parallel isolated reviewers,
   reported side by side, never merged. Fowler 12-smell baseline carried even
   when the repo documents nothing. Go/no-go gate preserved.
3. **`wait-what`** — auto corrective that re-pitches a missed message in plain
   language with CONTEXT.md vocabulary.
4. **`to-questionnaire`** — user loop; grills the SEND (recipient + what the
   user needs back), targets the gap, writes a fillable questionnaire.
5. **`debug` HITL loop template** — structured human-driven repro loop script;
   the other diagnosing-bugs deltas (no-correct-seam finding, tagged logs,
   ranked hypotheses) were already present (shared lineage).

## Rationale

- Their model treats the context window and the issue tracker as first-class
  resources; ours treats the filesystem (plan folders) as the resource. Both
  valid; margins live where our model is weak: interview mechanics, review
  separation, corrective loops, knowledge extraction, durable decisions.
- Their governance (prose CLAUDE.md, no validator) was deliberately NOT
  adopted — we keep `skill-forge audit` enforcement.
- Each mechanic is layer-compliant (§3), agnostic (§9), and under 500 lines
  (§15).

## Non-transfer (deliberate)

- Model-routing POLÍTICA v1-v10 are NOT migrated into this repo. They are
  harness-routing policy with a canonical home already:
  `~/.agents/ROUTING.md` (single source of truth per POLÍTICA v7's
  anti-drift rule). Duplicating them here would create a second source of
  truth and drift risk.
- Release machinery (changesets/CHANGELOG), dual harness manifests, and the
  `ask-matt` router were rejected — see `.out-of-scope/mattpocock-deferred-tier2.md`.

## Consequences

- Loops that interview (`grill`, `triage`, `deepen`) should run the
  `grilling` discipline instead of re-implementing the interview.
- Code reviews now cost two isolated review passes; reports stay separate.
- Future system decisions (and rejections) get recorded here — a decision is
  real only when a repo file carries it (§10).
