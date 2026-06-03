# Artificial Analysis API Reference

Source: https://artificialanalysis.ai/api/v2/data/llms/models  
Docs: https://artificialanalysis.ai/api-reference#free-api

## Authentication

```
x-api-key: <ARTIFICIAL_ANALYSIS_API_KEY>
```

Get a free key at https://artificialanalysis.ai/ (free account, 1,000 req/day).  
Set in `.env` as `ARTIFICIAL_ANALYSIS_API_KEY`.

**Attribution required:** include a link to https://artificialanalysis.ai/ when publishing data.

---

## GET /api/v2/data/llms/models

Returns LLM benchmarks, pricing, and speed metrics for all evaluated models.

### Response Envelope

```json
{
  "status": 200,
  "prompt_options": {
    "parallel_queries": 1,
    "prompt_length": "medium"
  },
  "data": [ <LLMModel> ]
}
```

> `prompt_length` defaults to `medium` (1k input tokens) for speed/latency data.

### LLMModel Object Fields

| Field | Type | Description |
| ----- | ---- | ----------- |
| `id` | string | Stable UUID — use as primary identifier |
| `name` | string | Full model name (may change) |
| `slug` | string | URL-friendly identifier (rarely changes) |
| `model_creator` | object | `{id, name, slug}` |
| `evaluations` | object | Benchmark scores (see below) |
| `pricing` | object | USD per million tokens |
| `median_output_tokens_per_second` | number | Generation speed |
| `median_time_to_first_token_seconds` | number | Time to first token |
| `median_time_to_first_answer_token` | number | Time to first non-reasoning token |

### Evaluations Object

| Field | Description | Range |
| ----- | ----------- | ----- |
| `artificial_analysis_intelligence_index` | Overall intelligence score | 0–100 |
| `artificial_analysis_coding_index` | Coding benchmark | 0–100 |
| `artificial_analysis_math_index` | Math benchmark | 0–100 |
| `mmlu_pro` | MMLU Pro (knowledge breadth) | 0–1 |
| `gpqa` | Graduate-level reasoning | 0–1 |
| `hle` | Humanity's Last Exam | 0–1 |
| `livecodebench` | Live coding benchmark | 0–1 |
| `scicode` | Scientific coding | 0–1 |
| `math_500` | MATH-500 | 0–1 |
| `aime` | AIME math competition | 0–1 |

### Pricing Object

**Note: these are USD per MILLION tokens** (different from OpenRouter's per-token values).

| Field | Description |
| ----- | ----------- |
| `price_1m_blended_3_to_1` | Blended price (3:1 input:output ratio) |
| `price_1m_input_tokens` | Input price per 1M tokens |
| `price_1m_output_tokens` | Output price per 1M tokens |

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
