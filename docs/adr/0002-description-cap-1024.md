# ADR-0002 — Description cap 1024 (not 1200), floor 200

Status: accepted
Date: 2026-08-05
Source: plan `2026-08-05-feature-description-cap`; research dispatched 2026-08-05
(5 parallel subagents, source-verified)

## Decision

`description` in SKILL.md frontmatter: MUST be 1..1024 chars, SHOULD be >= 200.
Enforced by `skill-forge audit` (1024 = FAIL, 200 = WARN). The user's proposed
1200 was rejected after research.

## Rationale

1024 is the Agent Skills ecosystem ceiling. Every spec-aligned harness draws the
line there:

| harness | cap | enforcement |
|---------|-----|-------------|
| agentskills.io spec | 1024 | mandates |
| Pi (primary) | 1024 | WARN >1024, still loads |
| Hermes | 1024 | HARD REJECT — "Description exceeds 1024 characters" |
| OpenCode | doc 1024 | not runtime-enforced (1200 loads, injected in full) |
| MiniMax Code | none per-desc | 20K aggregate catalog budget |
| Claude Code | spec 1024 / listing 1536 | truncation; 1% context budget |
| Codex | 1024 renderer | truncation with "..." |

Consequences of 1200: Pi warns on Andrés's primary harness, Hermes rejects the
skill outright, Codex/Claude silently truncate — chars past 1024 are wasted or
harmful. 1024 is the single number that is valid everywhere.

## Secondary decisions

- **Floor 200 (WARN):** descriptions under ~200 chars under-trigger (the
  entire triggering burden sits on the description). The 5 most condensed
  descriptions were rewritten to 324..446 chars with front-loaded trigger
  content (capability + use-case words in the first ~60 chars, because
  Hermes surfaces only the first 57).
- **"Use when" need not lead:** front-loading the trigger CONTENT is what
  matters; the phrase must appear but not necessarily first.
- **No per-description cap in MiniMax (20K aggregate)** and **OpenCode
  lenient runtime** were NOT grounds for a higher repo cap: the repo must
  stay valid in the strictest harness (Hermes) and the open standard.

## Consequences

- audit rejects >1024 (error) and <200 (warning, error under --strict).
- AGENTS.md §5/§15 carry the policy.
- Future descriptions must fit 200..1024 with front-loaded triggers.
