"""
OpenRouter API client for the analyze-model skill.

Public models endpoint works without an API key.
Optional: set OPENROUTER_API_KEY in .env or environment for authenticated requests.

Endpoint: GET https://openrouter.ai/api/v1/models
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"


def _load_env_key() -> str:
    """Resolve OPENROUTER_API_KEY from .env file or environment."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    return key


def _get_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    api_key = _load_env_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def fetch_models(output_modalities: str = "text") -> list[dict]:
    """
    Fetch all models from OpenRouter.

    Args:
        output_modalities: Comma-separated modalities to filter by.
            "text" (default), "image", "audio", "embeddings", "all"

    Returns:
        List of model objects. See references/openrouter-api.md for schema.

    Raises:
        urllib.error.HTTPError: On HTTP errors (401, 429, 500, etc.)
    """
    url = f"{OPENROUTER_API_BASE}/models?output_modalities={output_modalities}"
    req = urllib.request.Request(url, headers=_get_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("data", [])


def fetch_model_count(output_modalities: str = "text") -> int:
    """Fetch total model count from OpenRouter."""
    url = f"{OPENROUTER_API_BASE}/models/count?output_modalities={output_modalities}"
    req = urllib.request.Request(url, headers=_get_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("count", 0)
