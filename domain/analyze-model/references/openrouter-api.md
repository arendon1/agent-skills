# OpenRouter API Reference

Source: https://openrouter.ai/api/v1/models  
Docs: https://openrouter.ai/docs/guides/overview/models/llms-full.txt

## Authentication

```
Authorization: Bearer <OPENROUTER_API_KEY>
```

Key is optional for the public models endpoint. Set in `.env` as `OPENROUTER_API_KEY`.

---

## GET /api/v1/models

Returns the full list of available models.

### Query Parameters

| Parameter | Values | Default | Description |
| --------- | ------ | ------- | ----------- |
| `output_modalities` | `text`, `image`, `audio`, `embeddings`, `all` | `text` | Filter by output type |
| `supported_parameters` | `tools`, `reasoning`, etc. | — | Filter by capability |

### Response Schema

```json
{
  "data": [ <Model> ]
}
```

### Model Object Fields

| Field | Type | Description |
| ----- | ---- | ----------- |
| `id` | string | `provider/model-slug` — use this as `model_id` in usage logs |
| `canonical_slug` | string | Permanent slug (never changes) |
| `name` | string | Human-readable display name |
| `created` | number | Unix timestamp when added to OR |
| `description` | string | Capability description |
| `context_length` | number | Max context window (tokens) |
| `architecture` | object | Input/output modalities, tokenizer |
| `pricing` | object | **USD per token** (not per million) |
| `top_provider` | object | Primary provider limits |
| `supported_parameters` | string[] | Supported API params |
| `expiration_date` | string\|null | Deprecation date if applicable |

### Pricing Object

All values are **USD per token**.

| Field | Description |
| ----- | ----------- |
| `prompt` | Cost per input token |
| `completion` | Cost per output token |
| `request` | Fixed cost per request |
| `image` | Cost per image input |
| `web_search` | Cost per web search |
| `internal_reasoning` | Cost for reasoning tokens |
| `input_cache_read` | Cost per cached token read |
| `input_cache_write` | Cost per cached token write |

**Cost formula:**
```
cost = input_tokens * pricing.prompt + output_tokens * pricing.completion
```

**Example (deepseek-v4-flash-0731, $0.1399/M in · $0.2677/M out · $0.0024/M cached_read):**
```json
{
  "prompt": "0.0000001399",
  "completion": "0.0000002677",
  "request": "0",
  "image": "0",
  "web_search": "0",
  "internal_reasoning": "0",
  "input_cache_read": "0.0000000024",
  "input_cache_write": "0.0000001399"
}
```

### Architecture Object

```json
{
  "input_modalities": ["file", "image", "text"],
  "output_modalities": ["text"],
  "tokenizer": "Claude",
  "instruct_type": null
}
```

### Top Provider Object

```json
{
  "context_length": 200000,
  "max_completion_tokens": 64000,
  "is_moderated": false
}
```

---

## GET /api/v1/models/count

Returns total count matching the same query parameters.

```json
{ "count": 312 }
```

---

## Supported Parameters (capability flags)

| Value | Description |
| ----- | ----------- |
| `tools` | Function calling |
| `tool_choice` | Tool selection control |
| `max_tokens` | Response length limit |
| `temperature` | Randomness |
| `top_p` | Nucleus sampling |
| `reasoning` | Internal reasoning mode |
| `include_reasoning` | Return reasoning in response |
| `structured_outputs` | JSON schema enforcement |
| `response_format` | Output format |
| `stop` | Custom stop sequences |
| `seed` | Deterministic outputs |

---

## Error Codes

| Code | Meaning |
| ---- | ------- |
| 200 | Success |
| 401 | Invalid/missing API key |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
