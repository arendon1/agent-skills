"""
OpenCode usage bridge — extracts session token data from the OpenCode SQLite DB.

OpenCode DB schema (session table):
  id              TEXT   — session UUID
  model           TEXT   — JSON: {"id":"slug","providerID":"provider","variant":"..."}
  tokens_input    INT    — total input tokens for the session
  tokens_output   INT    — total output tokens for the session
  time_created    INT    — epoch milliseconds
  title           TEXT   — session title

Each session = one usage record. Sessions without token data are skipped.
"""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

SOURCE_HELP = (
    "Extracts usage from your OpenCode sessions database. "
    "Requires OpenCode CLI installed. "
    "Optionally pass --db-path if auto-discovery fails."
)


def _openode_bin() -> str:
    """Resolve the opencode binary for the current platform."""
    if sys.platform == "win32":
        return "opencode.cmd"
    return "opencode"


def _get_db_path(db_path: str | None = None) -> Path:
    if db_path:
        p = Path(db_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"Database not found at: {db_path}")

    try:
        result = subprocess.run(
            [_openode_bin(), "db", "path"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        path = result.stdout.strip()
        if path and Path(path).exists():
            return Path(path)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    home = Path.home()
    candidates = [
        home / ".local" / "share" / "opencode" / "opencode.db",
        home / "Library" / "Application Support" / "opencode" / "opencode.db",
        Path(os.environ.get("LOCALAPPDATA", "")) / "opencode" / "opencode.db",
    ]
    for c in candidates:
        if c.exists():
            return c

    raise FileNotFoundError(
        "Could not find OpenCode database. "
        "Specify --db-path manually, or install opencode CLI.\n"
        "Tried: opencode db path, and platform defaults."
    )


def _parse_model(raw: str) -> str:
    """Parse model JSON into a catalog-compatible model_id."""
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw

    provider = obj.get("providerID", "")
    model_id = obj.get("id", raw)

    if provider == "openrouter":
        return model_id
    if provider:
        return f"{provider}/{model_id}"
    return model_id


def _epoch_ms_to_iso(epoch_ms: int) -> str:
    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


_QUERY = (
    "SELECT id, model, tokens_input, tokens_output, time_created "
    "FROM session "
    "WHERE tokens_input > 0 OR tokens_output > 0 "
    "ORDER BY time_created"
)


def _query_sessions_via_cli() -> list[dict]:
    result = subprocess.run(
        [_openode_bin(), "db", _QUERY, "--format", "json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"opencode db query failed: {result.stderr.strip()}")

    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON from opencode db: {result.stdout[:200]}")

    if not isinstance(rows, list):
        rows = []
    return rows


def _query_sessions_via_sqlite(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(_QUERY)
        rows = [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
    return rows


def extract(output_path: str, **kwargs) -> list[dict]:
    user_path = kwargs.get("db_path")
    db_path = _get_db_path(user_path)

    if user_path:
        rows = _query_sessions_via_sqlite(db_path)
    else:
        rows = _query_sessions_via_cli()
    if not rows:
        print("Warning: No sessions with token data found.")
        return []

    records: list[dict] = []
    skipped = 0
    for row in rows:
        inp = row.get("tokens_input", 0) or 0
        out = row.get("tokens_output", 0) or 0
        if inp == 0 and out == 0:
            skipped += 1
            continue

        ts_raw = row.get("time_created")
        timestamp = _epoch_ms_to_iso(ts_raw) if ts_raw else ""
        model_id = _parse_model(row.get("model", ""))

        records.append({
            "timestamp": timestamp,
            "model_id": model_id,
            "input_tokens": int(inp),
            "output_tokens": int(out),
            "session_id": row.get("id", ""),
        })

    print(f"Extracted {len(records)} usage records from {len(rows)} sessions.")
    if skipped:
        print(f"  Skipped {skipped} sessions with zero tokens.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Saved to: {output.resolve()}")

    return records
