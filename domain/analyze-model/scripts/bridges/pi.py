"""
Pi usage bridge for analyze-model skill.

Extracts session token + cost data from Pi's JSONL session files.

Pi stores sessions at:
  ~/.pi/agent/sessions/<encoded-cwd>/<timestamp>_<uuid>.jsonl

Each session has a header followed by entries. Assistant messages carry:
  message.usage = {input, output, cacheRead, cacheWrite, reasoning, totalTokens, cost{...}}
  message.provider = e.g. "openrouter"
  message.model = e.g. "openai/gpt-5.6-luna-pro"

We emit one record per assistant message in the standard usage log format.
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

SOURCE_HELP = (
    "Extracts real LLM usage from your Pi agent session JSONL files at "
    "~/.pi/agent/sessions/. Each assistant message yields one record with "
    "input/output/cacheRead/cacheWrite/reasoning tokens, model, and Pi's "
    "logged cost. Requires Pi installed."
)


def _pi_sessions_dir() -> Path:
    home = Path.home()
    candidates = [
        home / ".pi" / "agent" / "sessions",
        Path("/root/.pi/agent/sessions"),
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"Could not find Pi sessions directory. Tried: {[str(c) for c in candidates]}"
    )


def extract(output_path: str, **kwargs) -> list[dict]:
    sessions_dir = _pi_sessions_dir()
    records = []
    skipped = 0
    sessions_seen = 0

    for jsonl in sessions_dir.rglob("*.jsonl"):
        sessions_seen += 1
        session_id = None
        current_model = None
        current_provider = None
        cwd = None
        for line in jsonl.open():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            t = obj.get("type")
            if t == "session":
                session_id = obj.get("id")
                cwd = obj.get("cwd")
            elif t == "model_change":
                current_provider = obj.get("provider")
                current_model = obj.get("modelId")
            elif t == "message":
                msg = obj.get("message", {})
                if msg.get("role") != "assistant":
                    continue
                usage = msg.get("usage")
                if not usage:
                    continue
                model_id = msg.get("model") or current_model
                provider = msg.get("provider") or current_provider
                if not model_id:
                    continue
                ts = obj.get("timestamp") or msg.get("timestamp")
                cost = usage.get("cost", {}) or {}
                records.append({
                    "timestamp": ts,
                    "model_id": model_id,
                    "provider": provider,
                    "input_tokens": usage.get("input", 0) or 0,
                    "output_tokens": usage.get("output", 0) or 0,
                    "cache_read_tokens": usage.get("cacheRead", 0) or 0,
                    "cache_write_tokens": usage.get("cacheWrite", 0) or 0,
                    "reasoning_tokens": usage.get("reasoning", 0) or 0,
                    "total_tokens": usage.get("totalTokens", 0) or 0,
                    "cost_input_usd": cost.get("input", 0) or 0,
                    "cost_output_usd": cost.get("output", 0) or 0,
                    "cost_cache_read_usd": cost.get("cacheRead", 0) or 0,
                    "cost_cache_write_usd": cost.get("cacheWrite", 0) or 0,
                    "cost_total_usd": cost.get("total", 0) or 0,
                    "session_id": session_id,
                    "cwd": cwd,
                })

    if not records:
        print("Warning: No Pi sessions with usage data found.")
        return []

    print(f"Extracted {len(records)} usage records from {sessions_seen} sessions.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Saved to: {output.resolve()}")
    return records
