# Forecast Module Analysis — analyze-model

Scout context for fixing the zero-clamp regression bug.

## Files Examined

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/forecast.py` | 1-565 | Full forecast engine + CLI |
| `evals/evals.json` | 1-18 | Single eval (cost analysis only) |

**No tests exist.** Zero test files in the entire skill. No evals for forecast.

---

## Architecture (data flow)

```
usage.json/csv
     │
     ▼
_load_usage() ───► list of {timestamp, model_id, input_tokens, output_tokens}
     │
     ▼
_daily_totals() ───► { "2026-06-06": {calls, input_tokens, output_tokens}, ... }
     │
     ├──► _linear_regression(daily_calls)     → call_slope, call_intercept
     ├──► _linear_regression(daily_input)     → input_slope, input_intercept
     ├──► _linear_regression(daily_output)    → output_slope, output_intercept
     │
     ▼
_project(slope, intercept, n_hist, horizon_days)  ───►  projected total (CLAMPED ≥0)
     │
     ▼
Model share allocation: total_proj × (model_calls / total_calls)
     │
     ▼
CLI printer: _print_forecast() → hbar() render
```

**Key insight:** The `projections.average` and `projections.worst_case` sections are computed independently at lines 413-423 and 397-403 — they bypass `_project()` entirely. This means they show valid data even when the main report outputs all zeros, creating a confusing mismatch.

---

## Sharp Edge 1 (CRITICAL): `_project()` zero-clamps silently

**File:** `scripts/forecast.py`, lines 231-238

```python
def _project(slope: float, intercept: float, n_hist: int, horizon_days: int) -> float:
    mid = n_hist + horizon_days / 2.0
    projected_daily = slope * mid + intercept
    return max(0.0, projected_daily) * horizon_days
```

**Problem:** When regression slope is negative (common for sparse/intermittent data), `projected_daily` at midpoint goes negative → clamped to 0 → entire forecast outputs `$0.00, 0 calls, 0 tokens`.

**Validation with actual data (8 days, Jun 6-14):**

| Horizon | slope | intercept | proj_daily at midpoint | Clamped result | Average baseline |
|---------|-------|-----------|----------------------|----------------|-----------------|
| 30d | -147,027 | 1,182,781 | -2,198,837 | **0** | 20,045,610 |
| 90d | -147,027 | 1,182,781 | -6,609,644 | **0** | 60,136,830 |
| 365d | -147,027 | 1,182,781 | -26,825,840 | **0** | 243,888,255 |

**Impact:** The `projected_total_cost_usd`, `projected_calls`, `projected_input_tokens`, `projected_output_tokens`, all `by_model[].projected_*` fields, and `projections.trend` are all zero — silently. The user sees `$0.00` with no warning.

---

## Sharp Edge 2: `_daily_totals()` ignores calendar gaps

**File:** `scripts/forecast.py`, lines 179-189

Only days with data appear. Days with zero usage (e.g., Jun 11) are absent. The regression uses indices [0..7] regardless of whether the span is 8 consecutive days or 8 scattered days over 3 months. This compresses time: the slope is computed over index-space, not calendar-space.

**Effect:** The slope is computed as if these 8 points are evenly spaced, which underestimates the decay when there are gaps (usage dropped to 0 on a gap day, but the regression doesn't see the zero).

---

## Sharp Edge 3: No error signaling when forecast fails

**File:** `scripts/forecast.py`, lines 345-347, 476-494

The `forecast()` function returns `projected_total_cost_usd: 0.0000` with no error flag. The CLI printer checks for an `"error"` key but nothing sets it. The CLI prints `Projected cost: $0.0000 USD` — indistinguishable from a legitimate all-zero forecast.

---

## Sharp Edge 4: No tests for the forecast module

- **Zero test files** across the entire skill
- **Single eval** only covers cost analysis, nothing about forecasting
- **No edge case coverage:** declining trends, single-day data, empty usage, all-zero tokens, highly variable data, model miss from catalog

---

## Sharp Edge 5: `_find_alternatives()` depends on projected cost

**File:** `scripts/forecast.py`, lines 259-317

Uses `target_info["projected_cost_usd"]` to compute `potential_savings_usd`. When projected cost is zero (bug), all savings are zero — the alternatives section becomes meaningless.

---

## Fix Strategy

**Recommended (minimum):** In `_project()`, add fallback to historical average when regression goes negative:

```python
def _project(slope: float, intercept: float, n_hist: int, horizon_days: int) -> float:
    mid = n_hist + horizon_days / 2.0
    projected_daily = slope * mid + intercept
    if projected_daily <= 0:
        avg_daily = intercept + slope * ((n_hist - 1) / 2.0)  # = y_mean
        return max(0.0, avg_daily) * horizon_days
    return projected_daily * horizon_days
```

**Better approach:** Return confidence alongside projection and show trend-vs-average comparison in CLI.

**Also fix:** `_daily_totals()` should zero-fill missing days between first and last.

---

## File Change Summary

| File | Change | Severity |
|------|--------|----------|
| `scripts/forecast.py:231-238` | `_project()`: fallback to historical average | CRITICAL |
| `scripts/forecast.py:179-189` | `_daily_totals()`: zero-fill missing days | MEDIUM |
| `scripts/forecast.py:345-347` | `forecast()`: emit warning when regression zero-clamps | LOW |
| `evals/evals.json` | Add forecast eval cases | MEDIUM |
| (new) test file | Test module for regression edge cases | MEDIUM |

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Identified 5 sharp edges with concrete file paths, line numbers, quantified data validation, fix strategy, and severity classification"
    }
  ],
  "changedFiles": [],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "python3 diagnostic of regression against 8-day usage data for horizons 30/90/365",
      "result": "passed",
      "summary": "Confirmed slope=-147K/day, projected daily goes negative for all horizons, clamped to 0 vs avg baseline of 20M/60M/243M tokens"
    },
    {
      "command": "find -name '*test*' and '*eval*' across skill directory",
      "result": "passed",
      "summary": "Zero test files found. Single eval in evals.json covers cost analysis only, not forecast"
    }
  ],
  "validationOutput": [
    "Horizon 30d: slope=-147,027, intercept=1,182,781, proj_daily=-2,198,837 → clamped 0 vs avg 20,045,610",
    "Horizon 365d: proj_daily=-26,825,840 → clamped 0 vs avg 243,888,255",
    "_daily_totals() produces 8 buckets for 9 calendar days (Jun 11 missing)",
    "forecast() returns no error flag when all projections are zero"
  ],
  "residualRisks": [
    "Average baseline may over-project if decline is real (usage genuinely dropping, not noise). A confidence-weighted blend between trend and average would be safer.",
    "_find_alternatives() uses projected cost which is zero when bug triggers — review even after _project fix."
  ],
  "noStagedFiles": true,
  "notes": "The core fix is one function (_project). The secondary fix (_daily_totals zero-fill) is also important but less severe. No tests exist — recommend adding at least 3 test cases: declining trend, flat trend, single-day data."
}
```