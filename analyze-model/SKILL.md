---
name: analyze-model
language: en-US
description: >-
  Fetches live model data from OpenRouter and Artificial Analysis APIs, merges
  benchmarks with pricing, runs deep cost analysis on usage logs, exports usage
  from LLM surfaces (OpenCode, VS Code, etc.), analyzes subscription efficiency,
  and forecasts future spend with cheaper-model alternatives.
  Use when comparing LLM costs or quality, analyzing total API spend from
  usage logs, exporting agent usage for cost analysis, evaluating subscription
  cost efficiency, forecasting future LLM costs, finding cheaper alternatives,
  or when the user asks about model pricing, intelligence index, speed, or
  token costs across providers.
invocation: user
layer: domain
loop: analyze-model
provides: [model-analysis]
deliverable: model cost/quality eval report
metadata:
  version: "1.0.0"
  risk_tier: LOW
---

# analyze-model

Queries **OpenRouter** and **Artificial Analysis** APIs to build a live model
catalog, then uses that catalog as the source of truth for cost analysis and
usage forecasting based on real usage logs.

## Authentication Setup

API keys resolved in this order for each provider:

1. `.env` file in the current workspace
2. Shell environment variable

| Provider             | Variable                      | Required? |
| -------------------- | ----------------------------- | --------- |
| OpenRouter           | `OPENROUTER_API_KEY`          | Optional (public models endpoint works without it) |
| Artificial Analysis  | `ARTIFICIAL_ANALYSIS_API_KEY` | Required  |

## Workflows

### analyze-model fetch-catalog

Fetches and merges model data from both APIs into a local catalog JSON.

script: `fetch_models.py`

```bash
python scripts/fetch_models.py --output catalog.json
# OpenRouter only:
python scripts/fetch_models.py --or-only --output catalog.json
# Artificial Analysis only:
python scripts/fetch_models.py --aa-only --output catalog.json
```

**Output fields per model:**

| Field | Source | Description |
| ----- | ------ | ----------- |
| `id` | OpenRouter | Unique model ID (`provider/slug`) |
| `name` | OpenRouter | Human-readable name |
| `context_length` | OpenRouter | Max context window (tokens) |
| `pricing.prompt` | OpenRouter | USD per input token |
| `pricing.completion` | OpenRouter | USD per output token |
| `aa.evaluations.artificial_analysis_intelligence_index` | AA | Overall intelligence score |
| `aa.evaluations.artificial_analysis_coding_index` | AA | Coding benchmark |
| `aa.median_output_tokens_per_second` | AA | Generation speed |
| `aa.median_time_to_first_token_seconds` | AA | Latency |

---

### analyze-model analyze-costs

Reads a usage log file and the catalog, then produces a cost breakdown by
model with totals, percentages, and per-call averages. **Resolves private-provider
model IDs** (e.g. `opencode-go/*`) to OpenRouter equivalents via `references/aliases.json`.
**Computes subscription efficiency** for token-budget providers by comparing
subscription cost vs. OpenRouter pay-per-token equivalent.

**Agent pre-flight:** Before running, check if subscription pricing is fresh:
```bash
python scripts/fetch_subscriptions.py
```
If the exit code is 1, dispatch subagents to research current pricing, then
write `references/subscriptions.json`. Proceed once cache is fresh.

script: `analyze_costs.py`

```bash
python scripts/analyze_costs.py usage.json --catalog catalog.json
python scripts/analyze_costs.py usage.csv  --catalog catalog.json --output report.json
```

**Usage log format** — see `references/usage-format.md`

**Output includes:**
- Total USD spent
- Calls, input tokens, output tokens (global + per model)
- Cost % share per model (sorted by spend) — **rendered as horizontal bars**
- Unknown models that could not be priced
- **Subscription efficiency** — monthly-bucketed with per-provider cap logic
- **Monthly sparklines** — cap usage trends per provider
- **Model jumping detection** — sessions with model switches flagged
- **Alias resolution** — private models matched to OpenRouter catalog

---

### analyze-model forecast

Projects future costs over a configurable horizon (default 30 days) using
linear trend extrapolation from historical usage. Includes cheaper-model
alternative recommendations.

script: `forecast.py`

```bash
python scripts/forecast.py usage.json --catalog catalog.json --days 30
python scripts/forecast.py usage.csv  --catalog catalog.json --days 90 --output forecast.json
```

**Output includes:**
- Projected total cost, calls, tokens for the horizon period (up to 365 days)
- Per-model projected cost with usage share — **rendered as horizontal bars**
- **Multi-baseline projections** — trend, worst-case, and average with comparison bars
- Up to 3 cheaper alternatives per top-cost model (requires `aa` enrichment in catalog)

---

### analyze-model export-usage

Exports usage data from an LLM surface into the standard usage log format that
`analyze_costs.py` and `forecast.py` consume.

script: `export_usage.py`

```bash
python scripts/export_usage.py --source opencode --output usage.json
python scripts/export_usage.py                    # interactive: pick a source
python scripts/export_usage.py --list-sources      # show available bridges
python scripts/export_usage.py --list-all          # include planned sources
```

**How agents should use this:** When a user asks about their LLM usage, costs,
or forecasting, prompt them to select a source. Ask: "Which LLM surface are you
using? I can extract from any supported surface (see `--list-sources`)." Then run the dispatcher with `--source`.

---

## Typical Analysis Pipeline

```bash
# Step 0 (agent): refresh subscription pricing if stale
python scripts/fetch_subscriptions.py

# Step 1: Build the catalog
python scripts/fetch_models.py --output catalog.json

# Step 2: Export your usage from an LLM surface
python scripts/export_usage.py --source opencode --output usage.json
# (or manually provide a usage log — see references/usage-format.md)

# Step 3: Cost breakdown (now with aliases + subscription efficiency)
python scripts/analyze_costs.py usage.json --catalog catalog.json --output cost_report.json

# Step 4: 30-day forecast + alternatives
python scripts/forecast.py usage.json --catalog catalog.json --days 30 --output forecast.json
```

---

## Quick Reference

| Action | Command |
| ------ | ------- |
| Fetch catalog | `python scripts/fetch_models.py --output catalog.json` |
| Analyze costs | `python scripts/analyze_costs.py <usage> --catalog catalog.json` |
| 30-day forecast | `python scripts/forecast.py <usage> --catalog catalog.json --days 30` |
| OpenRouter only | `python scripts/fetch_models.py --or-only --output catalog.json` |
| Export usage (opencode) | `python scripts/export_usage.py --source opencode --output usage.json` |
| List export sources | `python scripts/export_usage.py --list-sources` |

## Error Handling

| Code | Meaning | Action |
| ---- | ------- | ------ |
| 401 | Invalid/missing API key | Check `.env` or env variable |
| 429 | Rate limit (AA: 1000 req/day) | Wait, cache responses locally |
| 500 | Server error | Retry up to 3x with backoff |

## References

| Topic | File |
| ----- | ---- |
| OpenRouter API schema | `references/openrouter-api.md` |
| Artificial Analysis API schema | `references/artificialanalysis-api.md` |
| Usage log format spec | `references/usage-format.md` |
| Model aliases | `references/aliases.json` |
| Subscription pricing | `references/subscriptions.json` |

## Scripts

script: `export_usage.py` — Dispatcher for usage extraction from LLM surfaces.
script: `fetch_subscriptions.py` — Cache-gate for subscription pricing (30-day TTL).
script: `chart_utils.py` — ASCII chart rendering (horizontal bars, sparklines, gauges).
script: `bridges/opencode.py` — SQLite usage bridge for that surface.
script: `bridges/base.py` — Bridge protocol definition.
script: `client_openrouter.py` — OpenRouter HTTP client (models endpoint).
script: `client_aa.py` — Artificial Analysis HTTP client (LLMs endpoint).
script: `fetch_models.py` — Fetches from both APIs and merges into a unified catalog.
script: `analyze_costs.py` — Cost analysis engine; accepts JSON or CSV usage logs.
script: `forecast.py` — Linear-trend forecasting + cheaper-alternative finder.
