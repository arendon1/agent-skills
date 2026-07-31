# PLAN — use-herdr skill refinement (post v0.7.5)

## Mission

Determine whether anything new in herdr since v0.7.5 (released 2026-07-21) —
or anything in v0.7.5 itself not fully captured in the skill — requires the
use-herdr skill to be updated. If yes, propose the minimal set of edits.

## Background

- herdr 0.7.5 is installed locally (`/opt/homebrew/bin/herdr`, version 0.7.5).
- use-herdr SKILL.md was authored 2026-07-28 and documents v0.7.5.
- Two preview builds shipped after v0.7.5: `2026-07-29-44b3adb12552` and
  `2026-07-21-0f10e1453a7f` (per `gh release list --repo ogulcancelik/herdr`).
- The skill's commands/flags come from the 0.7.5 snapshot; previews may have
  landed new subcommands, flags, `--kind` values, or config sections.

## Tasks

| # | Task | Status |
|---|------|--------|
| T.1 | Research party: 4 parallel subagents (releases, CLI, agents, docs/community) | [x] |
| T.2 | Triangulate findings into RESEARCH.md with sources | [x] |
| T.3 | Diff findings against current SKILL.md + 4 references; identify gaps | [x] |
| T.4 | Apply concrete corrections: broken `--json` flag (10 sites), false "All commands accept --json" claim (2 sites), missing `HERDR_AGENT` env var (2 sites), missing `config check` + `api snapshot` (commands.md), missing `ui.sidebar_start_collapsed` + `ui.prompt_new_workspace_name` (commands.md), `pane_history` default note, known-issues section (headless restart, tmux, non-US keyboard), new MUST NOT for `--json` on creational verbs | [x] |
| T.5 | Run `skill-forge audit` on the refined skill; ensure exit 0 | [x] (PASS, 474 lines) |
| T.6 | Append LESSONS.md with 6 invariants (verify subagents, two copies of the skill, preview vs stable, `--json` selectively supported, subagent over-reporting, community > changelog) | [x] |

## Stop conditions

- v0.7.5 preview-only changes → no skill edit (preview is not stable).
- Stable-release change → minimal edit; preserve §MUST/§MUST NOT invariants.
- Documented CLI contradicts installed binary → prefer installed binary as
  ground truth; flag staleness in LESSONS.

## Right-size

This is a small-to-medium feature (skill refinement), not a full redesign.
Artifacts: `PLAN.md` + `RESEARCH.md` + `LESSONS.md`. No PRD/ARD/SPEC — the
existing skill is the spec; we're diffing it against a moving upstream.
