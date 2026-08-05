"""
Artificial Analysis API client for the analyze-model skill.

Requires: ARTIFICIAL_ANALYSIS_API_KEY in .env or environment variable.
Rate limit: 1,000 requests per day (free tier).

Endpoint: GET https://artificialanalysis.ai/api/v2/language/models/free

MIGRATION (2026-08-04): legacy /api/v2/data/llms/models retires 2026-11-04.
Replaced by /api/v2/language/models (Pro) or /api/v2/language/models/free.
We use the FREE tier, so free is the endpoint. See
references/artificialanalysis-api.md for the field diff.
"""

import os
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

AA_API_BASE = "https://artificialanalysis.ai/api/v2"
AA_MODELS_PATH = "/language/models/free"  # FREE replacement; Pro would be /language/models
_MAX_RETRIES = 3


def _load_api_key() -> str:
    """
    Resolve ARTIFICIAL_ANALYSIS_API_KEY from:
    1. ARTIFICIAL_ANALYSIS_API_KEY environment variable
    2. .env file in the current workspace
    """
    key = os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY", "")
    if key:
        return key
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ARTIFICIAL_ANALYSIS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    return key


def _get_headers() -> dict:
    key = _load_api_key()
    if not key:
        raise ValueError(
            "ARTIFICIAL_ANALYSIS_API_KEY not found. "
            "Add it to your .env file or set as environment variable:\n"
            "  ARTIFICIAL_ANALYSIS_API_KEY=your_key_here\n"
            "Get a key at: https://artificialanalysis.ai/ (free account)"
        )
    return {"x-api-key": key, "Content-Type": "application/json"}


def _request_with_retry(url: str) -> dict:
    """HTTP GET with exponential backoff on 429/500."""
    headers = _get_headers()
    for attempt in range(_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < _MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"Rate limited (429). Waiting {wait}s before retry {attempt + 2}/{_MAX_RETRIES}...")
                time.sleep(wait)
                continue
            if e.code == 500 and attempt < _MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError(f"Failed after {_MAX_RETRIES} attempts: {url}")


def _normalize_model(m: dict) -> dict:
    """Map a raw `language/models/free` model onto the legacy-compatible shape
    that fetch_models.py / forecast.py / analyze_costs.py already read.

    The free endpoint nests speed fields under `performance` (legacy had them at
    top level) and exposes fewer evaluation subfields. Normalizing here keeps
    the downstream contract stable across the migration.
    """
    out = dict(m)
    perf = m.get("performance")
    if isinstance(perf, dict):
        out.setdefault("median_output_tokens_per_second",
                       perf.get("median_output_tokens_per_second"))
        out.setdefault("median_time_to_first_token_seconds",
                       perf.get("median_time_to_first_token_seconds"))
        # legacy name has no _seconds suffix; consumers read this name
        out.setdefault("median_time_to_first_answer_token",
                       perf.get("median_time_to_first_answer_token_seconds"))
        out.setdefault("median_end_to_end_response_time_seconds",
                       perf.get("median_end_to_end_response_time_seconds"))
    return out


def _extract_rows(payload, url: str) -> list:
    """Envelope is not contractual ({'data': [...]} vs bare array). Accept both."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
    raise RuntimeError(f"Unexpected response shape from {url}: {type(payload).__name__}")


def fetch_llm_models() -> list[dict]:
    """
    Fetch LLM benchmark + pricing data from Artificial Analysis (free tier).

    Paginates the free endpoint (page_size capped at 200) and normalizes each
    model to the legacy-compatible shape:
      id, name, slug, model_creator, evaluations, pricing,
      median_output_tokens_per_second, median_time_to_first_token_seconds,
      median_time_to_first_answer_token.

    Raises:
        ValueError: If API key is not configured.
        urllib.error.HTTPError: On unrecoverable HTTP errors.
    """
    page = 1
    models: list[dict] = []
    while True:
        url = f"{AA_API_BASE}{AA_MODELS_PATH}?page={page}"
        payload = _request_with_retry(url)
        data = _extract_rows(payload, url)
        models.extend(_normalize_model(m) for m in data)
        # Stop when the API reports no more pages; bare-array responses (no
        # pagination) are single-shot and break after the first page.
        if isinstance(payload, dict):
            pag = payload.get("pagination") or {}
            try:
                total = int(pag.get("total_pages", page))
            except (TypeError, ValueError):
                total = page
            if not pag.get("has_more") or page >= total:
                break
        else:
            break
        page += 1
    return models
