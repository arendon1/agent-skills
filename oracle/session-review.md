---
type: oracle-review
date: 2026-06-14
subject: analyze-model refactor + M3 subagent assignments
agent: oracle (forked, model=opencode-go/minimax-m3 per new override)
---

# Session Review — analyze-model Refactor & M3 Assignments

## Executive Summary

The session produced a clean refactor in the deployed runtime location and a sensible-looking model assignment, but **drift exists between deployed and source-of-truth**: the git-tracked source repo at `~/storage/shared/Projects/agent-skills/analyze-llm-model/` was not renamed. This is the highest-priority gap. The M3 assignment is reasonable but premature — 20 sample calls in 8 days is not a sufficient signal to commit three production subagents.

Severity: **1 critical drift, 1 medium risk, several minor gaps**.

---

## 1. Drift / Contradictions

### 🔴 CRITICAL: Source repo not synchronized with deployed rename

| Location | Path | SKILL.md frontmatter | Status |
|----------|------|----------------------|--------|
| Deployed (runtime) | `~/.pi/agent/skills/analyze-model/` | `name: analyze-model` | ✅ Renamed |
| **Source-of-truth (git)** | `~/storage/shared/Projects/agent-skills/analyze-llm-model/` | `name: analyze-llm-model` | ❌ **Still old name** |
| `chart_utils.py` docstring in source | — | "ASCII chart utilities for analyze-llm-model output." | ❌ **Not updated** |
| Folder name in source | `analyze-llm-model/` | — | ❌ **Not renamed** |
| Source SKILL.md workflow headers | 5 occurrences of `/analyze-llm-model` | — | ❌ **Not updated** |

**Impact**: Next time the source repo is deployed (e.g. via skill-forge `deploy.py`, or a fresh `~/.pi/agent/skills/` rebuild), the old name will come back. The git history will not record this rename. The vault config in `_notes/config/skills.md` references the source path — it will become stale on next sync.

**Fix**: The source repo at `~/storage/shared/Projects/agent-skills/` needs the same rename applied to its `analyze-llm-model/` subdirectory, plus a `git mv` + commit so the rename is version-controlled.

### Other drift points (all consistent across deployed + vault)

- Settings override: `subagents.agentOverrides.{oracle,planner,reviewer}.model = "opencode-go/minimax-m3"` — applied. Verified.
- Vault files: `skills.md`, `recovery.md`, `daily/2026-06-09.md` — all renamed. Verified.
- Catalog freshness: 337 models (76 AA-enriched) — `minimax/minimax-m3` is present. Verified.
- Aliases.json: `opencode-go/minimax-m3` → `minimax/minimax-m3` mapping present (line 12). Verified.

No other contradictions found.

---

## 2. Missing Analysis

The cost report is well-structured but has gaps that limit the actionability of the M3 recommendation:

### 2.1 M3 has no calibration data

- Total M3 calls in 8 days: **20**
- Total V4 Pro calls in 8 days: **3,289**
- M3 sample is **0.6% of total volume** — statistically meaningless for quality comparison
- The IQ delta of +3.2 is from Artificial Analysis's synthetic benchmarks, not from real-world task completion
- **Risk**: we are trusting AA's IQ score as a proxy for *Andrés's actual task quality* on M3 vs V4 Pro. These often diverge.

**Recommendation**: Before committing three subagents to M3, run a controlled comparison — same task on both models, eyeball the outputs. Five to ten paired tasks would give meaningful signal.

### 2.2 Heavy-session breakdown missing

- The June 6 day had 545 calls and 1.24M tokens — 2.4× the average
- The report doesn't identify which sessions drove this
- It also doesn't break down by hour-of-day or weekday-vs-weekend
- Without this, we don't know if the usage pattern is sustainable (heavy once, then a week of catch-up) or representative

### 2.3 Subagent cost tracking gap

- `analyze_costs.py` output included: `"Subagent model usage is untracked at the DB level."`
- The OpenCode Go model-jumping detection (line 333+ in analyze_costs.py) attempts a `subprocess.run(["opencode", "db", ...])` query
- This appears to be broken or incomplete — it logged 0 of 77 sessions with model switches
- **Implication**: when M3 is assigned to oracle/planner/reviewer, those subagent calls will be attributed to V4 Pro (the parent session's default), or worse, dropped entirely

**Recommendation**: Investigate the `model_jumps` detection and confirm subagent calls are correctly attributed to their actual model in `usage.json`.

### 2.4 Coding Index ignored

- M3 Coding Index: 43.4
- V4 Pro Coding Index: not surfaced in the report
- For coding-heavy tasks (worker, reviewer), coding index is more relevant than general IQ
- The current assignment uses IQ for all three quality-sensitive agents, including `reviewer` (which reviews code) and `planner` (which plans code work)

**Recommendation**: Pull coding index for all AA-enriched models in scope and reconsider whether `reviewer` and `planner` should use coding-index ranking instead of general IQ.

---

## 3. Model Assignment Strategy

### What's right
- Splitting quality-sensitive (oracle, planner, reviewer) from implementation (worker) is a defensible principle
- IQ delta of +3.2 across all three is a meaningful tier upgrade per the skill's own comparison rules (Δ ≤ 2 same-tier, Δ 3–5 budget-tier with warning)
- M3 is also 14% cheaper per call, so this is not a cost increase

### What's risky
- **Three production agents on a model with 20 sample calls** — there is no signal that M3 will perform well on Andrés's actual work, only on AA's synthetic benchmarks
- **No fallback model configured** — if M3 is unavailable, the override takes the whole subagent down
- **No phased rollout** — all three are switched at once. If M3 underperforms, you have three broken subagents, not one
- **Oracle uses fork context** — the oracle on M3 will see this same session history and may exhibit confirmation bias toward the M3 recommendation

### Suggested phased rollout

| Phase | Action | Validation |
|-------|--------|------------|
| 1 | M3 → oracle only (read-only, low blast radius) | 5–10 sessions; eyeball oracle's drift-detection quality |
| 2 | Add M3 → planner (writes plan.md, reviewable) | 5–10 plans; compare against V4 Pro plans on same tasks |
| 3 | Add M3 → reviewer (reads + critiques) | 5–10 reviews; check if M3 catches more issues or different issues |
| 4 (optional) | Test M3 → worker | Only if phases 1–3 validate quality on real work |

This trades speed-to-rollout for safety. The current all-at-once rollout assumes M3 will be good; the phased rollout assumes it might not be and validates first.

---

## 4. Risks Not Surfaced

1. **Settings override syntax is unvalidated at runtime** — the parent edited `settings.json` directly. A typo in `agentOverrides` key would silently fall back to default. Worth running `subagent({ action: "doctor" })` or `/subagents-doctor` to confirm the override loaded.

2. **M3's first impression is sticky** — if M3 returns a low-quality first answer on a subagent task, the human reviewer (Andrés) might pre-judge the model. The first 5–10 M3 outputs should be treated as calibration, not as the final verdict.

3. **The `opencode-go/` provider marks up M3** — the parent noted in the June 9 daily that "OC Go marks up V4 Pro 4× over OR market rate." We don't know M3's markup. If M3 is also marked up 4×, the "14% cheaper than V4 Pro" claim is on the marked-up price, not on OR market. Need to confirm pricing for `opencode-go/minimax-m3` directly.

4. **Forecast regression bug is more serious than reported** — the `_project()` zero-clamp doesn't just affect 365-day forecasts. With 8 days of skewed data (heavy first 3, then drop-off), the 30-day forecast also went to zero. Any horizon longer than ~8 days is unreliable on this data pattern. The fix should be: floor at historical average daily rate when regression goes negative, not zero.

5. **The Obsidian note's chart axes mix scales** — the daily activity chart shows tokens and `cost × 1000` on the same y-axis. The `0.614` value for cost×1000 is roughly the same visual height as `1,244,230` tokens. The chart looks like the data is on the same scale, but they are not. A reader will misread this.

---

## 5. Is forecast.py the Right Next Step?

**No.** Higher-priority items, in order:

1. **Sync the source repo rename** (governance). Without this, the refactor is incomplete and at risk.
2. **Validate M3 with paired tasks** (calibration). The 20-sample assumption is fragile.
3. **Add fallback models to agent overrides** (resilience). One line each.
4. **Fix `chart_utils`/note scale mixing** (correctness of the report we just published).
5. **Fix `_project()` floor** (real bug, but workaround exists for now).

The forecast.py fix is a real bug but the impact is bounded — manual reports work around it, and the SKILL.md doesn't promise 365-day accuracy. The source-repo drift is unbounded — it will cause silent regressions on the next deploy.

---

## 6. Recommendations Summary

| Priority | Action | Effort |
|----------|--------|--------|
| 🔴 P0 | Rename `analyze-llm-model/` → `analyze-model/` in the source repo; `git mv` + commit | 5 min |
| 🟡 P1 | Phase the M3 rollout: oracle first, then planner, then reviewer | 10 min config + 1 day observation |
| 🟡 P1 | Add `fallbackModels: ["opencode-go/deepseek-v4-pro"]` to each M3 override | 2 min |
| 🟡 P1 | Run `/subagents-doctor` to verify the override loaded | 1 min |
| 🟢 P2 | Validate M3 with 5–10 paired tasks vs V4 Pro | 30 min |
| 🟢 P2 | Fix `_project()` to floor at historical average instead of zero | 10 min |
| 🟢 P2 | Recompute Obsidian note chart on separate y-axes (tokens / cost) | 10 min |
| ⚪ P3 | Investigate subagent cost attribution in `model_jumps` detection | 30 min |
| ⚪ P3 | Surface coding index alongside IQ in the cost report | 1 hr |

---

## 7. Oracle Recommendation

The M3 assignment is directionally correct and well-intentioned, but premature. The right move is:

1. **Stop the all-at-once rollout** — keep M3 on `oracle` only for now
2. **Revert planner and reviewer to default** (inherit V4 Pro) until M3 is validated
3. **Fix the source-repo drift first** — it's a 5-minute fix that protects the entire refactor
4. **Then** validate M3 with real tasks before committing the other two agents

This preserves the upside of the IQ upgrade while avoiding the downside of betting on a model with 20 sample calls.

The parent session's instinct was right (M3 is genuinely better in theory). The execution was too aggressive (three production agents, no fallback, no calibration phase).
