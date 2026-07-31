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
- [ ] `python3 utility/skill-forge/scripts/init.py use-hunk --invocation auto --layer domain --provides code-review-pause --path domain/`
- [ ] `mv use-hunk/ domain/use-hunk/` if init created at root
- **Acceptance**: folder `domain/use-hunk/` exists with stub SKILL.md, scripts/, references/

## T2 — Write SKILL.md (orchestration layer)

- [ ] frontmatter: name, description with literal "Use when", invocation auto, layer domain, provides code-review-pause, language en-US, metadata version
- [ ] body, agnostic prose (no harness/model/tool names per §9):
  - Purpose: pause-for-review orchestration
  - The model: 4 decision points (trigger, surface, resume, annotations)
  - Prerequisite: gate on `command -v hunk`
  - Workflow A: keyword pause flow
  - Workflow B: risk-aware auto-pause flow
  - Workflow C: surface selection (cmux → herdr → manual) — *abstracted*, references handle harness specifics
  - Workflow D: resume classification (approve/feedback/stop/ambiguous)
  - When to stop (every pause = explicit operator signal, never assume)
  - Boundaries (MUST/MUST NOT)
  - References table
- **Acceptance**: SKILL.md < 500 lines, passes `python3 utility/skill-forge/scripts/audit.py use-hunk --strict`

## T3 — Write references/ (harness-specific, not audited)

- [ ] `references/surfaces.md` — how to detect cmux vs herdr vs manual; what the surface call looks like for each (load use-cmux or use-herdr skill transitively)
- [ ] `references/lexicon.md` — full approve/feedback/stop word lists (es/en), ambiguity-flag pattern
- [ ] `references/risk-thresholds.md` — default thresholds, how to override, examples of triggering diffs
- [ ] `references/hunk-cli.md` — minimal hunk session API reference (subset of `hunk skill path` output, distilled for orchestration use only; reference NOT vendor)
- **Acceptance**: 4 reference files exist, each < 300 lines, body may name specific tools (NOT audited by skill-forge)

## T4 — Validate

- [ ] `python3 utility/skill-forge/scripts/audit.py use-hunk --strict` → PASS
- [ ] `python3 utility/skill-forge/scripts/manifest.py` (regenerate) + `--check` (verify fresh)
- [ ] grep safety pass: no `pi`, `Claude Code`, `OpenCode`, `Cursor`, `Antigravity`, `subagent`, `TodoWrite`, `soul_recall`, `~/.claude/`, `~/.pi/` in SKILL.md prose (code blocks OK)
- **Acceptance**: zero audit warnings, manifest up to date

## T5 — Smoke test in herdr (end-to-end)

Pre-req: herdr server running; an isolated git repo as test fixture.

- [ ] start herdr server: `herdr server start` (or `herdr server` if not detached)
- [ ] create test workspace from a tiny git repo: `mkdir -p /tmp/hunk-test && cd /tmp/hunk-test && git init && echo a > a.txt && git add . && git commit -m init`
- [ ] open workspace in herdr: `herdr workspace create --cwd /tmp/hunk-test --label hunk-test --no-focus`
- [ ] split pane for hunk: `herdr pane split --current --direction right --no-focus` → record PANE_ID
- [ ] open hunk in that pane: `herdr pane run "$PANE_ID" "hunk diff"`
- [ ] from the original pane, run `hunk session list --json` → expect 1 session
- [ ] modify a.txt, stage: `echo b >> a.txt` (no commit yet, working tree)
- [ ] verify hunk auto-reloaded (or send `hunk session reload --repo /tmp/hunk-test -- diff`)
- [ ] run `hunk session review --repo /tmp/hunk-test --json` → expect hunk structure with 1 file
- [ ] add comment via `hunk session comment add --repo /tmp/hunk-test --file a.txt --new-line 2 --summary "verify the appended b"`
- [ ] verify comment appears: `hunk session comment list --repo /tmp/hunk-test --json`
- [ ] close workspace: `herdr workspace close <ws_id>`
- **Acceptance**: every command above succeeds, JSON outputs are sane, no hunk session broker errors

## T6 — Agent-loop test (simulated operator)

In a real session, simulate the pause → operator message → resume cycle:

- [ ] operator: "add a helper function src/utils.py that does foo"
- [ ] agent: writes code, detects risk threshold not crossed, no pause (autonomous)
- [ ] operator: "refactor auth to use the new helper across 5 files"
- [ ] agent: detects risk (5 files, auth), auto-pauses; prints preamble; opens hunk in herdr pane; loads hunk-review; verifies session; leaves one inline note on the riskiest file
- [ ] operator (simulated): "go"
- [ ] agent: classifies as approve, proceeds
- [ ] operator: "hmm"
- [ ] agent: flags ambiguity, asks
- [ ] operator: "aborta"
- [ ] agent: reverts working tree, acknowledges

**Acceptance**: all 6 messages classified correctly, no autonomous resume, no false approvals

## T7 — Commit, push, install globally

- [ ] `git status` → confirm only domain/use-hunk/ + .claude-plugin/marketplace.json changes
- [ ] `git add domain/use-hunk/ .claude-plugin/marketplace.json`
- [ ] `git commit -m "feat(use-hunk): orchestration skill for pause-for-review via hunk"`
- [ ] `git push` (or HTTPS if SSH fails)
- [ ] `npx -y skills add . -g -y` → installs to ~/.agents/skills/use-hunk/ + symlinks to ~/.pi/agent/skills/
- [ ] restart pi → verify `use-hunk` appears in skill list
- **Acceptance**: skill discoverable in pi, manifest clean, no audit regressions in existing skills

## T8 — Update CONTEXT.md (ubiquitous language)

- [ ] add entry: `hunk review pause` — agent stops at explicit keyword or risk threshold, prints preamble, opens hunk in cmux/herdr/manual, waits for operator approve/feedback/stop/ambiguous message
- **Acceptance**: CONTEXT.md updated, term cross-referenced

## Test plan summary

| Test | Type | Covers |
|---|---|---|
| T5 herdr smoke | shell | surface (herdr), hunk CLI mechanics, session broker |
| T6 agent loop | conversational | trigger (A+B), preamble, surface, resume classification, ambiguity flag, rollback |
| T4 audit | static | constitution compliance, agnostic body, manifest freshness |
| manual | post-deploy | real review session with operator |

## Out of scope (deferred)

- Web-based review surface
- Multi-human collaboration
- Operator-authored inline notes (hunk's `c` key) — already supported by hunk itself, no skill work needed
- Config UI for risk thresholds — file-based config in v1, UI later if needed
