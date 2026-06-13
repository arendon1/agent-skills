# Usage Log Format

The `analyze_costs.py` and `forecast.py` scripts accept usage logs in **JSON** or **CSV** format.

---

## JSON Format

An array of call records:

```json
[
  {
    "timestamp": "2026-05-15T10:30:00Z",
    "model_id": "anthropic/claude-sonnet-4-5",
    "input_tokens": 1500,
    "output_tokens": 800,
    "session_id": "optional-session-id",
    "task_id": "optional-task-id"
  }
]
```

Also accepted with an envelope:

```json
{
  "data": [ ... ]
}
```

### Field Reference

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `timestamp` | string | Yes (for `forecast.py`) | ISO 8601 datetime. Used for trend computation. |
| `model_id` | string | Yes | OpenRouter model ID (`provider/model`). Must match catalog. |
| `input_tokens` | integer | Yes | Tokens sent to the model (prompt). |
| `output_tokens` | integer | Yes | Tokens received from the model (completion). |
| `session_id` | string | No | Optional grouping by session. |
| `task_id` | string | No | Optional task/job identifier. |

### Supported Timestamp Formats

| Format | Example |
| ------ | ------- |
| `%Y-%m-%dT%H:%M:%SZ` | `2026-05-15T10:30:00Z` |
| `%Y-%m-%dT%H:%M:%S` | `2026-05-15T10:30:00` |
| `%Y-%m-%dT%H:%M:%S.%fZ` | `2026-05-15T10:30:00.123Z` |
| `%Y-%m-%d %H:%M:%S` | `2026-05-15 10:30:00` |
| `%Y-%m-%d` | `2026-05-15` |

---

## CSV Format

Headers must include: `timestamp`, `model_id`, `input_tokens`, `output_tokens`.

```csv
timestamp,model_id,input_tokens,output_tokens,session_id
2026-05-15T10:30:00Z,anthropic/claude-sonnet-4-5,1500,800,session-001
2026-05-15T11:00:00Z,google/gemini-2.5-pro,2200,1200,session-002
2026-05-15T14:20:00Z,openai/gpt-4o,900,450,session-003
```

---

## Exporting Usage from Common Sources

### OpenCode

OpenCode does not currently expose a machine-readable usage log file. Workarounds:

1. **Manual tracking**: Add a logging wrapper that appends to a `usage.json` file on each completion.
2. **OpenRouter activity**: If you route through OpenRouter, export activity from the dashboard.

### OpenRouter Dashboard

1. Go to https://openrouter.ai/activity
2. Use the date range filter
3. Download CSV or copy the table

Match exported `model` column values to OpenRouter model IDs (e.g., `claude-sonnet-4-5` -> `anthropic/claude-sonnet-4-5`).

### Custom Logging Snippet (Python)

```python
import json
from pathlib import Path
from datetime import datetime, timezone

def log_usage(model_id: str, input_tokens: int, output_tokens: int, session_id: str = ""):
    log_path = Path("usage.json")
    entries = json.loads(log_path.read_text()) if log_path.exists() else []
    entries.append({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model_id": model_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "session_id": session_id,
    })
    log_path.write_text(json.dumps(entries, indent=2))
```

---

## model_id Mapping

`model_id` must match OpenRouter's `id` field format: `provider/model-slug`.

Common examples:

| Model | OpenRouter model_id |
| ----- | ------------------- |
| Claude Sonnet 4.5 | `anthropic/claude-sonnet-4-5` |
| Claude 3.5 Sonnet | `anthropic/claude-3-5-sonnet` |
| GPT-4o | `openai/gpt-4o` |
| Gemini 2.5 Pro | `google/gemini-2.5-pro-preview` |
| Llama 3.3 70B | `meta-llama/llama-3.3-70b-instruct` |
| Deepseek R1 | `deepseek/deepseek-r1` |

To verify IDs, run:
```bash
python scripts/fetch_models.py --or-only | python -m json.tool | grep '"id"'
```
