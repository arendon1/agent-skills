# PLAN — use-hunk skill

## Status legend

- `[ ]` pending
- `[~]` in progress
- `[x]` done
- `[!]` blocked

## T1 — Scaffold skill folder

- [x] investigate hunk (modem-dev) + verify brew install v0.17.7
- [x] grill operator on 4 design points (trigger, surface, resume, annotations)
- [x] create plan folder + PRD + ARD
- [x] `python3 utility/skill-forge/scripts/init.py use-hunk --invocation auto --layer domain --provides code-review-pause --path domain/`
- [x] scaffold landed at `domain/use-hunk/` (init --path honored)
- **Acceptance**: folder `domain/use-hunk/` exists with stub SKILL.md, scripts/, references/ — PASS

## T2 — Write SKILL.md (orchestration layer)

- [x] frontmatter: name, description with literal "Use when", invocation auto, layer domain, provides code-review-pause, language en-US, metadata version
- [x] body, agnostic prose (no harness/model/tool names per §9):
  - Purpose: pause-for-review orchestration
  - The model: 4 decision points (trigger, surface, preamble/inline, resume)
  - Prerequisite: gate on `command -v hunk`
  - Workflow A: keyword pause flow
  - Workflow B: risk-aware auto-pause flow
  - Workflow C: surface selection (cmux → herdr → manual) — *abstracted*, references handle harness specifics
  - Workflow D: resume classification (approve/feedback/stop/ambiguous)
  - When to stop (every pause = explicit operator signal, never assume)
  - Boundaries (MUST/MUST NOT)
  - References table
- [x] SKILL.md 321 lines (< 500), passes `audit.py domain/use-hunk --strict`

## T3 — Write references/ (harness-specific, not audited)

- [x] `references/surfaces.md` — cmux vs herdr vs manual detection, what the surface call looks like for each (delegates to use-cmux or use-herdr)
- [x] `references/lexicon.md` — full approve/feedback/stop word lists (es/en), ambiguity-flag pattern, classifier algorithm, verb-stem approach
- [x] `references/risk-thresholds.md` — default thresholds, how to override, examples
- [x] `references/hunk-cli.md` — minimal hunk session API surface (NOT vendored, points to `hunk skill path`)

## T4 — Validate

- [x] `audit.py domain/use-hunk --strict` → PASS
- [x] `manifest.py` (regenerate) + `--check` (verify fresh) — 40 skills, 3 groups
- [x] grep safety: SKILL.md prose clean (hunk/cmux/herdr named as external CLIs, no internal tool names)

## T5 — Smoke test in herdr (end-to-end)

- [x] herdr server already running
- [x] test fixture: `git init` in /tmp/hunk-test, single file a.txt
- [x] `herdr workspace create --cwd /tmp/hunk-test --label hunk-smoke --no-focus` → w9
- [x] `herdr pane split --pane w9:p1 --direction right --no-focus` → w9:p2
- [x] `herdr pane run w9:p2 "cd /tmp/hunk-test && hunk diff"` → broker registered session d6246073
- [x] `hunk session list --json` → 1 session, repoRoot=/private/tmp/hunk-test
- [x] modify a.txt (+d, +NEW LINE), `hunk session reload --repo /tmp/hunk-test -- diff` → 1 file, 1 hunk, +2/-0
- [x] `hunk session comment add --repo . --file a.txt --new-line 5 --summary "smoke test..."` → comment mcp:696756c8
- [x] `printf '{"comments":[...]}' \| hunk session comment apply --repo . --stdin` → 2nd comment mcp:b8f842db
- [x] `hunk session navigate --repo . --file a.txt --hunk 1` → focused
- [x] `hunk session review --repo . --include-patch --json` → raw patch returned (119 bytes)
- [x] `herdr workspace close w9` → broker shows 0 sessions

## T6 — Agent-loop test (classifier + ambiguity)

- [x] `python3 domain/use-hunk/scripts/test_classifier.py` → 30/30 PASS
  - T6 scenarios from PLAN: go, dale, rename, use-approach, hmm, abort, ??, etc. all classified correctly
  - Edge cases: empty, ?, ✓, 👍, +1, thanks, mixed languages, "Stop changing", "Did you really change X?", "esto está mal", auto, skip-review, refactor, backticks, -ing/-ed forms

## T7 — Commit, push, install globally

- [x] `git status` clean for the right files (only domain/use-hunk/, .claude-plugin/marketplace.json, docs/plans/)
- [x] `git add` + `git commit` — feat(use-hunk) — 10 files, 1445 insertions
- [x] `git push origin main` — `3d5c36f..069143f`
- [x] `npx -y skills add . -g -y` (from repo root) — installed to `~/.agents/skills/use-hunk/` + symlink to `~/.pi/agent/skills/use-hunk -> ../../../.agents/skills/use-hunk`

## T8 — Update CONTEXT.md (ubiquitous language)

- [x] added 4 terms: `hunk review pause`, `resume bucket`, `preamble`, `trigger override`
- [x] committed + pushed (`docs(context): add hunk review pause, resume bucket, preamble, trigger override`)

## Test plan summary

| Test | Type | Covers | Result |
|---|---|---|---|
| T5 herdr smoke | shell | surface (herdr), hunk CLI mechanics, session broker, comments, navigate, raw patch | PASS |
| T6 agent loop (classifier) | unit | trigger (A+B), preamble scope, surface, resume classification, ambiguity flag, rollback precedence | 30/30 PASS |
| T4 audit | static | constitution compliance, agnostic body, manifest freshness | PASS strict |
| post-deploy | manual | real review session with operator | pending — first session |

## Out of scope (deferred)

- Web-based review surface
- Multi-human collaboration
- Operator-authored inline notes (hunk's `c` key) — already supported by hunk itself, no skill work needed
- Config UI for risk thresholds — file-based config in v1, UI later if needed

## Notes for next iteration

- The classifier test should run in CI when the lexicons are edited. Add it to a pre-commit hook or a `make test` target in agent-skills.
- If the operator wants per-project risk threshold config, add `thresholds` to the project-level `.hunk/config.toml` and read it from there too (currently only reads `~/.config/agent-skills/use-hunk.toml`).
- Consider adding a `use-hunk --dry-run` mode that prints the would-be preamble + surface choice without actually pausing — useful for debugging the trigger logic without interrupting flow.
