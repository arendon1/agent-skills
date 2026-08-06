# PRD — Process-layer Tier 1: adopt verified margins from mattpocock/skills

## Mission

Adopt 6 verified margins from `mattpocock/skills` into our process layer.
Each margin already validated against our constitution (§9 agnosticism, §3
layers, §5 frontmatter, §15 size). Keep our strengths: `skill-forge audit`
enforcement, artifact ownership, go/no-go gates. Copy mechanics, not machinery.

## Background

- Scanned `mattpocock/skills` (2026-08-05) vs ours: 39 vs 40 skills.
- Their model: context window + issue tracker as first-class resources.
  Ours: filesystem plan folders. Both valid; margins live where our model
  is weak (interview mechanics, review separation, corrective loops,
  knowledge extraction, durable decisions).
- Their gap: zero enforcement (prose CLAUDE.md, no validator). We keep
  `skill-forge audit`. Do NOT adopt their governance model.
- Analysis agreed by user. This plan = Tier 1 only.

## Scope

| id | Requirement | Source |
|----|-------------|--------|
| R1 | Extract `grilling` primitive: frontier/rounds interview algorithm + facts-are-agent's-job (non-blocking subagent dispatch). Reusable by `grill` + future skills (`triage`, `deepen`). `grill` (user loop) runs it; grilling owns no artifacts. | mattpocock `grilling` |
| R2 | Two-axis `review`: Standards + Spec as **parallel subagents**, reported side-by-side, never merged. Add Fowler 12-smell baseline. Keep REFUTE + go/no-go gate. | mattpocock `code-review` |
| R3 | New `wait-what` skill: re-pitch corrective. User says "wait what"/confused -> agent re-pitches with context, plain language, CONTEXT.md vocabulary. | mattpocock `wait-what` |
| R4 | New `to-questionnaire` skill: inverse of grill. Blocker = knowledge in third party's head. Grill the *send* (recipient + what you need back), target the gap, output fillable questionnaire. | mattpocock `to-questionnaire` |
| R5 | `debug` deltas: (a) no-correct-seam = architectural finding -> handoff; (b) tagged `[DEBUG-xxx]` logs convention; (c) ranked falsifiable hypotheses shown to user before testing. | mattpocock `diagnosing-bugs` |
| R6 | ADR + out-of-scope infra for the skills system: `docs/adr/` + `.out-of-scope/` at repo root. Migrate POLÍTICA v1-v10 from soul memory -> ADRs. Seed `.out-of-scope/` with rejected-from-Matt list. AGENTS.md §6 gains ADR convention line. | mattpocock `.agents/adr/`, `.out-of-scope/` |

## Out of scope (deliberately rejected this pass)

- `wayfinder` decision-ticket model (needs ClickUp adaptation; separate plan).
- expand-contract wide-refactor pattern in `plan`/`build` (Tier 2).
- `writing-for-agents` quality discipline (Tier 2).
- Human-facing docs pages (Tier 2).
- `wizard` (GitHub-secrets-centric; our secrets stack differs).
- changesets/CHANGELOG release machinery (personal repo, no distribution).
- Dual harness manifests (we ship multi-harness via `npx skills add`).
- `ask-matt` router as a skill (AGENTS.md layer table covers).
- `teach` — no delta; shared lineage already.

## Success criteria

- Every new/changed SKILL.md passes `skill-forge audit --strict` (exit 0).
- `manifest.py --check` passes (manifest fresh after new skills).
- No harness/tool names in any new/changed skill body (§9).
- `grill` behavior preserved: still creates plan folder + PRD.md; now runs
  the frontier algorithm internally (one round per frontier, not one q).
- `review` behavior preserved: still REFUTES, still ends in go/no-go gate;
  now two axes, separate subagent contexts, side-by-side report.
- `docs/adr/` exists with >= 1 POLÍTICA migrated; `.out-of-scope/` seeded.
- Each new/changed SKILL.md < 500 lines (§15).

## Risks

- Primitive extraction can bloat `grill` -> guard: grilling owns NO artifact
  writes; grill keeps ownership (§6).
- Two-axis review doubles agent calls -> acceptable: reviews are rare,
  high-blast-radius; context separation is the point.
- POLÍTICA migration loses nuance in compression -> keep decision+rationale
  pairs verbatim-ish; ADR = decision record, not essay.
