"""
Artificial Analysis API client for the analyze-model skill.

Requires: ARTIFICIAL_ANALYSIS_API_KEY in .env or environment variable.
Rate limit: 1,000 requests per day (free tier).

Endpoint: GET https://artificialanalysis.ai/api/v2/data/llms/models
"""

import os
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

AA_API_BASE = "https://artificialanalysis.ai/api/v2"
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


def fetch_llm_models() -> list[dict]:
    """
    Fetch LLM benchmark + pricing data from Artificial Analysis.

    Returns:
        List of model objects. See references/artificialanalysis-api.md for schema.
        Each model includes: id, name, slug, model_creator, evaluations,
        pricing, median_output_tokens_per_second, median_time_to_first_token_seconds.

    Raises:
        ValueError: If API key is not configured.
        urllib.error.HTTPError: On unrecoverable HTTP errors.
    """
    url = f"{AA_API_BASE}/data/llms/models"
    data = _request_with_retry(url)
    return data.get("data", [])
