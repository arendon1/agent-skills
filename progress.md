# Progress

## Status
In Progress — Oracle review complete on analyze-model refactor + M3 assignments

## Tasks

### 🔴 P0 — source repo rename (CRITICAL drift)
- [ ] Rename `~/storage/shared/Projects/agent-skills/analyze-llm-model/` → `analyze-model/`
- [ ] Update SKILL.md frontmatter + 5 workflow headers in source repo
- [ ] Update `chart_utils.py`, `client_aa.py`, `client_openrouter.py` docstrings
- [ ] `git mv` + commit on master

### 🟡 P1 — Phase the M3 rollout
- [ ] Revert `planner` and `reviewer` overrides to default
- [ ] Keep `oracle` on M3 only
- [ ] Add `fallbackModels: ["opencode-go/deepseek-v4-pro"]` to oracle override
- [ ] Run `/subagents-doctor` to verify override loaded

### 🟡 P1 — M3 calibration (after P0)
- [ ] Run 5–10 paired tasks on M3 vs V4 Pro
- [ ] Eyeball oracle quality on drift detection
- [ ] If validated → add planner to M3
- [ ] If validated → add reviewer to M3

### 🟢 P2 — Skill quality fixes
- [ ] Fix `forecast.py` `_project()` to floor at historical average (not zero)
- [ ] Recompute Obsidian note daily-activity chart on separate y-axes
- [ ] Investigate subagent cost attribution in `model_jumps` detection
- [ ] Surface coding index alongside IQ in cost report

## Files Changed

- `oracle/session-review.md` — 167 lines, full review of refactor + M3 assignment (created 2026-06-14)

## Notes

- The source-of-truth git repo at `~/storage/shared/Projects/agent-skills/analyze-llm-model/` was NOT renamed when the deployed runtime copy at `~/.pi/agent/skills/analyze-model/` was. This is the highest-priority gap — next deploy will silently revert the rename.
- M3 (IQ 54.7) was assigned to oracle, planner, reviewer based on AA benchmark + 14% cost advantage vs V4 Pro (IQ 51.5). But M3 has only 20 sample calls in 8 days (0.6% of volume) — not enough to validate the IQ delta translates to real task quality.
- The forecast.py regression bug (`_project()` clamps negative slopes to zero) is real but a manual workaround exists; deprioritize in favor of P0 source repo sync.
- The Obsidian note daily-activity chart has a scale-mixing problem (tokens and cost×1000 on the same y-axis); will be misread.
- Subagent model usage is untracked at the OpenCode DB level per `analyze_costs.py` output — when M3 is assigned to subagents, those calls may be attributed to the wrong model in `usage.json`.
