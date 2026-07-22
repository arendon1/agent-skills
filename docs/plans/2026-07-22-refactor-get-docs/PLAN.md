# PLAN — get-docs refactor

> Plan: `2026-07-22-refactor-get-docs`

## Tasks

| # | Task | Status | Done when |
|---|---|---|---|
| 1 | Create plan folder + PRD.md | x | `PRD.md` written (4.6 KB) |
| 2 | `git mv utility/ctx7 → utility/get-docs` | x | `utility/get-docs/SKILL.md` exists, old gone |
| 3 | Rewrite SKILL.md (frontmatter + body) | x | 295 lines, exception declared, materialization rules in |
| 4 | Patch `.claude-plugin/marketplace.json` | x | `./utility/get-docs` |
| 5 | Drop `references/firecrawl-selfhost-workflow.md` (out of scope for v2) | x | `references/` removed |
| 6 | `audit.py get-docs` → exit 0 | x | PASS |
| 7 | `manifest.py --check` → exit 0 | x | PASS (35 skills, 3 groups) |
| 8 | Ad-hoc E2E verification (sandbox + ctx7 real + materialize + dedupe) | x | 11/11 pass |
| 9 | LESSONS.md (surfaces L1 — `ctx7 library` returns N>1 candidates) | x | `LESSONS.md` written |
| 10 | Commit (conventional, NO caveman) | [ ] | Next step |

## Sequencing

Tasks 2 → 3 → 4 → 5 filesystem. Tasks 6 → 7 gates. Task 8 E2E.
Task 9 conditional on E2E surfacing invariants (it did). Task 10 closes.

## E2E evidence (sandbox run, 2026-07-22)

- ctx7 already installed → backend = `cli`
- `ctx7 library firecrawl` → 5 candidates, top hit `/firecrawl/firecrawl-docs` (4302 snippets, score 83.6)
- `ctx7 docs /firecrawl/firecrawl-docs "self-host OPENAI_BASE_URL"` → 37 lines head
- Materialized `<sandbox>/docs/stack/firecrawl-docs/self-host-openai-base-url.md` (2127 bytes)
- Read back: frontmatter has `library`, `materialized_by`, `trust_score`
- Dedupe: re-run leaves content unchanged (hash stable)
- SKILL.md has `Deployability caveat` section + `architecture_exception` in frontmatter

## L1 surfaced

`ctx7 library <name>` returns N>1 candidates; top hit by score is not always
the docs repo. See LESSONS.md L1. Fix proposed but **not shipped** in v2.0.0
— requires intent-classification step. Documented for next iteration.

## Done

Tasks 1-9 [x]. Task 10 is the conventional commit.

Commit message:

```
refactor(utility): rename ctx7 -> get-docs + materialization to docs/stack/

- Frontmatter: name=ctx7 -> get-docs, version 1.1.0 -> 2.0.0, adds
  provides: [ctx7-cli, stack-grounding, docs-materializer] + a declared
  architecture_exception (AGENTS.md §12) explaining why this utility
  writes to the active project's FS under docs/stack/<lib>/<topic>.md.
- Body: replaces "Setup (one-time, per machine)" with STEP 0 that
  auto-installs ctx7 + degrades to REST. Adds STEP 3 materialize with
  dedupe rule (30d freshness window + _Refreshed: line) and STEP 4
  triangulate guidance.
- Drops references/firecrawl-selfhost-workflow.md (out of scope for v2;
  use-firecrawl owns that recipe).
- Adds Deployability caveat at top of body so consumers know the
  FS-write behavior is intentional.

Plan: docs/plans/2026-07-22-refactor-get-docs/
LESSONS L1: ctx7 library returns N>1 candidates; documented, fix proposed.
```
