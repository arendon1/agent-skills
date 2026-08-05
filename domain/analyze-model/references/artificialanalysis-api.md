# Artificial Analysis API Reference

Source: https://artificialanalysis.ai/api/v2/language/models/free  
Docs: https://artificialanalysis.ai/api-reference

## ⚠️ MIGRATION (2026-08-04)

Legacy endpoint `/api/v2/data/llms/models` retires **2026-11-04** (returns `410 Gone`
after). Replaced by documented V2 contract:

| Tier | Endpoint | Fields |
| ---- | -------- | ------ |
| Free (this client) | `GET /api/v2/language/models/free` | **Fewer fields** than legacy |
| Pro | `GET /api/v2/language/models` | Full set |

This client uses the **free** replacement (`client_aa.py` → `AA_MODELS_PATH =
"/language/models/free"`). We have a free account/key (1,000 req/day), not Pro.

**Action taken (2026-08-04, VERIFIED with live key):**
- `client_aa.py` now hits `/language/models/free`, paginates
  (`?page=N`, page_size capped at 200; ~591 models total vs legacy's 591),
  and **normalizes** each model back to the legacy-compatible shape so
  `fetch_models.py` / `forecast.py` / `analyze_costs.py` are unchanged.
- Speed fields arrive nested under `performance` on free; the client flattens
  them to top level (`median_output_tokens_per_second`,
  `median_time_to_first_token_seconds`, `median_time_to_first_answer_token`).
- The two evaluation fields the forecast pipeline needs are present on free:
  `artificial_analysis_intelligence_index`, `artificial_analysis_coding_index`
  (plus a new `artificial_analysis_agentic_index`). The rest of the legacy
  evaluation table (math, mmlu_pro, gpqa, …) no longer ships on free → Pro.
- `pricing` keeps `price_1m_input_tokens` / `price_1m_output_tokens` (plus
  cache fields, null on free). `price_1m_blended_3_to_1` is NOT returned by
  free; no consumer reads it (forecast computes its own 3:1 blend).

Guide: https://artificialanalysis.ai/data-api/migrate-v2-data

## Authentication

```
x-api-key: <ARTIFICIAL_ANALYSIS_API_KEY>
```

Get a free key at https://artificialanalysis.ai/ (free account, 1,000 req/day).  
Set in `.env` as `ARTIFICIAL_ANALYSIS_API_KEY`.

**Attribution required:** include a link to https://artificialanalysis.ai/ when publishing data.

---

## GET /api/v2/language/models/free

Returns LLM benchmarks, pricing, and speed metrics for all evaluated models
(Free tier — fewer fields than legacy `/data/llms/models`).

### Response Envelope (free)

```json
{
  "tier": "free",
  "intelligence_index_version": "4.1",
  "pagination": { "page": 1, "page_size": 200, "total_pages": 3, "has_more": true },
  "data": [ <LLMModel> ]
}
```

> **Pagination:** `data` is capped at 200 rows per page. The client loops
> `?page=1..total_pages` until `has_more` is false.

### LLMModel Object Fields

| Field | Type | Description |
| ----- | ---- | ----------- |
| `id` | string | Stable UUID — use as primary identifier |
| `name` | string | Full model name (may change) |
| `slug` | string | URL-friendly identifier (rarely changes) |
| `model_creator` | object | `{id, name, slug}` |
| `evaluations` | object | Benchmark scores (see below) |
| `pricing` | object | USD per million tokens |
| `performance` | object | Speed/latency metrics (nested on free) |
| `release_date` | string | `YYYY-MM-DD` |

**Raw free model shape** nests the speed fields under `performance`:

```json
"performance": {
  "median_output_tokens_per_second": 83.09,
  "median_time_to_first_token_seconds": 2.03,
  "median_time_to_first_answer_token_seconds": 2.03,
  "median_end_to_end_response_time_seconds": 8.05
}
```

**Normalization in `client_aa.py`** (`_normalize_model`) flattens these back to
top level so downstream consumers keep working:
`median_output_tokens_per_second`, `median_time_to_first_token_seconds`,
`median_time_to_first_answer_token` (legacy name, no `_seconds` suffix),
`median_end_to_end_response_time_seconds` (kept).

### Evaluations Object (free)

| Field | Description | Range |
| ----- | ----------- | ----- |
| `artificial_analysis_intelligence_index` | Overall intelligence score | 0–100 |
| `artificial_analysis_coding_index` | Coding benchmark | 0–100 |
| `artificial_analysis_agentic_index` | Agentic benchmark (new on free) | 0–100 |

> The legacy evaluation table (math, mmlu_pro, gpqa, hle, …) no longer ships on
> free — available on Pro only.

### Pricing Object (free)

**Note: these are USD per MILLION tokens** (different from OpenRouter's per-token values).

| Field | Description |
| ----- | ----------- |
| `price_1m_input_tokens` | Input price per 1M tokens |
| `price_1m_output_tokens` | Output price per 1M tokens |
| `price_1m_cache_hit_tokens` / `price_1m_cache_write_tokens` | Cache pricing (null on free) |

> `price_1m_blended_3_to_1` is NOT returned by free. No consumer reads it —
> `forecast.py` computes its own 3:1 blend.

**Conversion to match OpenRouter pricing:**
```python
# AA -> per-token (to compare with OpenRouter pricing.prompt/completion)
prompt_per_token    = price_1m_input_tokens  / 1_000_000
completion_per_token = price_1m_output_tokens / 1_000_000
```

### Example Response

```json
{
  "id": "2dad8957-4c16-4e74-bf2d-8b21514e0ae9",
  "name": "o3-mini",
  "slug": "o3-mini",
  "model_creator": {
    "id": "e67e56e3-15cd-43db-b679-da4660a69f41",
    "name": "OpenAI",
    "slug": "openai"
  },
  "evaluations": {
    "artificial_analysis_intelligence_index": 62.9,
    "artificial_analysis_coding_index": 55.8,
    "artificial_analysis_math_index": 87.2,
    "mmlu_pro": 0.791,
    "gpqa": 0.748,
    "hle": 0.087,
    "livecodebench": 0.717,
    "scicode": 0.399,
    "math_500": 0.973,
    "aime": 0.77
  },
  "pricing": {
    "price_1m_blended_3_to_1": 1.925,
    "price_1m_input_tokens": 1.1,
    "price_1m_output_tokens": 4.4
  },
  "median_output_tokens_per_second": 153.831,
  "median_time_to_first_token_seconds": 14.939,
  "median_time_to_first_answer_token": 14.939
}
```

---

## Rate Limits

| Tier | Limit |
| ---- | ----- |
| Free API | 1,000 requests / day |

Response headers:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`  
- `X-RateLimit-Reset`

---

## Error Codes

| Code | Meaning |
| ---- | ------- |
| 200 | Success |
| 401 | Invalid/missing API key |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
