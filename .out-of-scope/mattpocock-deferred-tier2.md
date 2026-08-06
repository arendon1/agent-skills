# Out of scope — deferred/rejected (from mattpocock/skills comparison, 2026-08-05)

Each item was consciously ruled out of Tier 1. If one is re-proposed, it must
be re-justified against the reason below — do not re-adopt on enthusiasm.

## Deferred to Tier 2 (not rejected)

- **wayfinder decision-ticket model** — multi-session fog planning (map,
  decision tickets, HITL/AFK, claim-by-assignment, native blocking). Needs
  ClickUp adaptation via `use-clickup`. Heaviest flow; only worth it when
  Andrés actually hits multi-session fog work.
- **expand-contract wide-refactor pattern** — mechanical refactors whose blast
  radius fans across the codebase; sequence expand → migrate in batches →
  contract. Missing tool in `plan`; adopt with a small PLAN.md amendment.
- **writing-for-agents quality discipline** — context pointers, the two loads,
  information hierarchy, leading words, negation, pruning. Could become a
  utility skill or fold into `skill-forge` as a quality mode; also target for
  slimming bloated domain SKILL.mds via disclosed references.
- **Human-facing docs pages** — per-skill 4-section pages (What it does / When
  to reach / Common questions / It's working if). Discoverability + a
  verification criterion per skill.

## Rejected (keep rejected)

- **changesets/CHANGELOG release machinery** — personal repo, no distribution;
  git history is the changelog.
- **Dual harness manifests** (plugin.json + per-skill openai.yaml) — we already
  ship multi-harness via `npx skills add` with symlinks.
- **ask-matt internal router skill** — AGENTS.md layer table + call rules cover
  it; at most a main-flow section in AGENTS.md, not a skill.
- **wizard (HITL interactive bash)** — GitHub-secrets-centric; our secrets
  stack differs. Revisit only if the HITL-provisioning pattern is wanted.
- **setup-matt-pocock-skills equivalent** — `bootstrap` + `skill-add` already
  cover session and install setup.
- **Their governance model** (prose trust, no validator) — we keep
  `skill-forge audit` enforcement. Non-negotiable.
