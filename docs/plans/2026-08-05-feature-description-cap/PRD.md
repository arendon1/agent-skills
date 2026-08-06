# PRD — Description cap 1024 + floor 200 + richer trigger descriptions

## Mission

Add a description char policy to the constitution + audit, aligned to the
Agent Skills ecosystem ceiling (1024), and rewrite the condensed descriptions
that under-trigger. Research-backed: 5 harnesses + the open standard, all
agree on 1024.

## Background (research, 2026-08-05)

| harness | cap | enforcement | model sees |
|---------|-----|-------------|------------|
| agentskills.io spec | 1..1024 | mandates | name+desc always in context |
| Pi (primary) | 1024 | WARN >1024 | full desc |
| OpenCode | doc 1024 | not runtime-enforced | full desc |
| Hermes | 1024 | HARD REJECT | first 57 chars only |
| MiniMax Code | none per-desc | 20K catalog budget | full desc |
| Claude Code | 1024 spec / 1536 listing | truncation | 1% budget, drops overflow |
| Codex | 1024 renderer | truncation | 2% budget, desc = sole trigger |

- 1200 was rejected: Pi warns >1024, Hermes rejects entirely, Codex/Claude
  truncate. Chars past 1024 are wasted or harmful.
- Current repo: NO description char limit exists. The "500" is the SKILL.md
  LINE limit (§15). 10 descriptions already >500 chars; none >1024.
- Current min = 140 (use-clickup). Condensed set: use-clickup 140,
  gestionar-cursos 194, skill-forge 208, research-literature 254,
  generar-paper 275.
- Trigger quality: description carries the ENTIRE triggering burden.
  Front-load "Use when" (Hermes surfaces only first 57 chars).

## Scope

| id | Requirement |
|----|-------------|
| R1 | `description` MUST be 1..1024 chars (ecosystem ceiling). Enforce FAIL in audit. |
| R2 | `description` SHOULD be >= 200 chars. Enforce WARN in audit. |
| R3 | Front-load "Use when" / "Usa cuando" trigger phrase (Hermes 57-char surface). |
| R4 | Rewrite 5 condensed descriptions to 300..500 chars with rich trigger vocabulary. |
| R5 | AGENTS.md §5 + §15 amendment: char policy + front-load guidance. |
| R6 | audit.py: MAX_DESC_CHARS=1024 (FAIL), MIN_DESC_CHARS=200 (WARN). |
| R7 | ADR-0002: why 1024 not 1200 (with harness evidence table). |

## Out of scope

- Trigger-eval methodology (20-query should/shouldn't suites) — Tier 2.
- Rewriting all 43 descriptions — only the condensed set.
- Changing other frontmatter fields (name/compatibility/etc.).

## Success criteria

- audit.py enforces both bounds; synthetic test: >1024 FAIL, <200 WARN.
- All 43 descriptions pass `audit --strict` (0 errors, 0 warnings).
- 5 rewritten descriptions land in 300..500 chars, front-loaded "Use when".
- AGENTS.md carries the policy; ADR-0002 records the evidence.
- Manifest fresh; pushed to origin/main.

## Risks

- Rewrites bloat past 1024 — guard: keep 300..500 target, verify per skill.
- es-CO skills (gestionar-cursos, generar-paper, research-literature) must
  keep single-language ("Usa cuando") — no en/es mixing (§5).
