"""
Base HTTP client for the ClickUp API.
Handles authentication, request configuration, and response caching.
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class ClickUpCache:
    """File-based response cache with endpoint-aware TTL."""

    CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
    CACHE_FILE = CACHE_DIR / "api_cache.json"

    # TTL in seconds by endpoint pattern
    TTL_STATIC = 1800       # 30 min — user, teams, spaces
    TTL_STRUCTURAL = 300    # 5 min — folders, lists
    TTL_TASKS = 60          # 1 min — task lists (change frequently)

    TTL_PATTERNS = [
        (re.compile(r"^/user$"), TTL_STATIC),
        (re.compile(r"^/team$"), TTL_STATIC),
        (re.compile(r"^/team/\d+/space"), TTL_STATIC),
        (re.compile(r"^/space/\d+$"), TTL_STRUCTURAL),
        (re.compile(r"^/space/\d+/folder"), TTL_STRUCTURAL),
        (re.compile(r"^/folder/\d+$"), TTL_STRUCTURAL),
        (re.compile(r"^/folder/\d+/list"), TTL_STRUCTURAL),
        (re.compile(r"^/space/\d+/list"), TTL_STRUCTURAL),
        (re.compile(r"^/list/\d+/task"), TTL_TASKS),
        (re.compile(r"^/team/\d+/task"), TTL_TASKS),
        (re.compile(r"^/tasks"), TTL_TASKS),
    ]
    DEFAULT_TTL = 300  # 5 min for unknown GET endpoints

    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> dict:
        """Load cache from file, return empty dict on any error."""
        if not self.CACHE_FILE.exists():
            return {}
        try:
            with open(self.CACHE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self):
        """Write cache to file atomically."""
        tmp = self.CACHE_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        tmp.replace(self.CACHE_FILE)

    @staticmethod
    def _cache_key(method: str, endpoint: str, params: Optional[dict] = None) -> str:
        """Generate a deterministic cache key."""
        raw = f"{method}:{endpoint}"
        if params:
            raw += ":" + json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _ttl_for(self, endpoint: str) -> int:
        """Resolve TTL for an endpoint by pattern matching."""
        for pattern, ttl in self.TTL_PATTERNS:
            if pattern.search(endpoint):
                return ttl
        return self.DEFAULT_TTL

    def get(self, method: str, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        """Return cached response if valid, else None."""
        key = self._cache_key(method, endpoint, params)
        entry = self._data.get(key)
        if not entry:
            return None
        ttl = self._ttl_for(endpoint)
        if time.time() - entry["ts"] > ttl:
            del self._data[key]
            return None
        return entry["response"]

    def set(self, method: str, endpoint: str, response: dict, params: Optional[dict] = None):
        """Store a response in the cache."""
        key = self._cache_key(method, endpoint, params)
        self._data[key] = {
            "ts": time.time(),
            "response": response,
        }
        self._save()

    def invalidate(self):
        """Clear the entire cache."""
        self._data = {}
        if self.CACHE_FILE.exists():
            self.CACHE_FILE.unlink(missing_ok=True)

class CachedResponse:
    """Minimal response-like object for cached data."""

    def __init__(self, data: dict):
        self._json = data
        self.status_code = 200

    def json(self) -> dict:
        return self._json

    def raise_for_status(self):
        pass  # cached responses are always successful


class ClickUpClient:
    """ClickUp API client with error handling and retries."""

    BASE_URL = "https://api.clickup.com/api/v2"
    V3_BASE_URL = "https://api.clickup.com/api/v3"
    TIMEOUT = 30  # seconds
    MAX_RETRIES = 3

    def __init__(self):
        self.api_key = self._get_api_key()
        self.team_id = self._get_team_id()
        self.cache = ClickUpCache()
        self.session = self._create_session()

    def _get_api_key(self) -> str:
        """
        Resolves the API key in order:
        1. .env in current workspace
        2. CLICKUP_API_KEY environment variable
        3. Clear error if not found
        """
        # 1. Look for .env in current workspace
        load_dotenv()

        # 2. Look in environment variables
        api_key = os.getenv("CLICKUP_API_KEY")

        if api_key:
            return api_key

        # 3. Error if not found
        raise RuntimeError(
            "CLICKUP_API_KEY not found. "
            "Configure your API key:\n"
            "1. Create a .env file with: CLICKUP_API_KEY=your_api_key\n"
            "2. Or export the variable: export CLICKUP_API_KEY=your_api_key"
        )

    def _get_team_id(self) -> Optional[str]:
        """
        Resolves the default team/workspace ID in order:
        1. .env in current workspace (CLICKUP_TEAM)
        2. CLICKUP_TEAM environment variable
        3. None — caller must resolve team at runtime
        """
        team_id = os.getenv("CLICKUP_TEAM")
        return team_id or None

    def _create_session(self) -> requests.Session:
        """Creates an HTTP session with common headers."""
        session = requests.Session()
        session.headers.update({
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        return session

    def request(self, method: str, endpoint: str, base_url: Optional[str] = None, **kwargs) -> requests.Response:
        """
        Executes an HTTP request with automatic retries and caching.

        GET requests check the cache first. POST/PUT/DELETE invalidate
        the cache before executing.

        Args:
            method: GET, POST, PUT, DELETE
            endpoint: API path (e.g., /tasks, /workspaces/{id}/docs)
            base_url: Override base URL (default: BASE_URL for v2).
                      Use V3_BASE_URL for Docs/Chat endpoints.
            **kwargs: Additional arguments for requests (params, json, etc.)

        Returns:
            Response from requests

        Raises:
            RuntimeError on authentication error
            requests.exceptions.RequestException if it fails after retries
        """
        if base_url is None:
            base_url = self.BASE_URL

        # Mutations invalidate the entire cache
        if method in ("POST", "PUT", "DELETE"):
            self.cache.invalidate()

        # Check cache for GET requests
        if method == "GET":
            params = kwargs.get("params")
            cached = self.cache.get(method, endpoint, params)
            if cached is not None:
                # Return a synthetic response-like object
                cached_response = CachedResponse(cached)
                return cached_response  # type: ignore[return-value]

        url = f"{base_url}{endpoint}"

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.TIMEOUT,
                    **kwargs
                )

                # Handle specific errors
                if response.status_code == 401:
                    raise RuntimeError(
                        "Invalid or expired ClickUp API key. "
                        "Verify your API key at https://app.clickup.com/settings"
                    )

                if response.status_code == 403:
                    raise RuntimeError(
                        "No permissions for this operation. "
                        "Verify that your API key has access to the resource."
                    )

                # If successful or non-recoverable error, return
                if response.status_code < 500:
                    # Cache successful GET responses
                    if method == "GET" and response.status_code < 400:
                        try:
                            params = kwargs.get("params")
                            self.cache.set(method, endpoint, response.json(), params)
                        except Exception:
                            pass  # never let cache failures break the request
                    return response

                # Server error - retry
                response.raise_for_status()

            except requests.exceptions.RequestException:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                # Exponential backoff: 1s, 2s, 4s
                import time
                time.sleep(2 ** attempt)

        return response

    # Convenience HTTP methods
    def get(self, endpoint: str, **kwargs):
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs):
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs):
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs):
        return self.request("DELETE", endpoint, **kwargs)

    # v3 API methods (Docs, Chat)
    def v3_get(self, endpoint: str, **kwargs):
        return self.request("GET", endpoint, base_url=self.V3_BASE_URL, **kwargs)

    def v3_post(self, endpoint: str, **kwargs):
        return self.request("POST", endpoint, base_url=self.V3_BASE_URL, **kwargs)

    def v3_put(self, endpoint: str, **kwargs):
        return self.request("PUT", endpoint, base_url=self.V3_BASE_URL, **kwargs)

    def v3_delete(self, endpoint: str, **kwargs):
        return self.request("DELETE", endpoint, base_url=self.V3_BASE_URL, **kwargs)


# Global client instance (lazy loading)
_client: Optional[ClickUpClient] = None

def get_client() -> ClickUpClient:
    """Returns the singleton client instance."""
    global _client
    if _client is None:
        _client = ClickUpClient()
    return _client


def get_team_id() -> Optional[str]:
    """Returns the default team/workspace ID from CLICKUP_TEAM env var, or None."""
    return get_client().team_id


from datetime import datetime

def iso_to_milliseconds(iso_date: str) -> int:
    """
    Converts ISO 8601 date to Unix epoch milliseconds.

    Args:
        iso_date: String in YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format

    Returns:
        Integer in milliseconds

    Examples:
        >>> iso_to_milliseconds("2026-01-26")
        1704067200000
    """
    # Try simple YYYY-MM-DD format
    try:
        date = datetime.strptime(iso_date[:10], "%Y-%m-%d")
        return int(date.timestamp() * 1000)
    except ValueError:
        pass

    # Try full ISO format
    try:
        date = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
        return int(date.timestamp() * 1000)
    except ValueError:
        pass

    raise ValueError(f"Invalid date format: {iso_date}. Use YYYY-MM-DD")


def milliseconds_to_iso(milliseconds: int) -> str:
    """
    Converts Unix epoch milliseconds to ISO 8601.

    Args:
        milliseconds: Integer in milliseconds

    Returns:
        String in YYYY-MM-DD format
    """
    date = datetime.fromtimestamp(milliseconds / 1000)
    return date.strftime("%Y-%m-%d")


def milliseconds_to_iso_full(milliseconds: int) -> str:
    """
    Converts milliseconds to ISO 8601 with time.

    Returns:
        String in YYYY-MM-DD HH:MM:SS format
    """
    date = datetime.fromtimestamp(milliseconds / 1000)
    return date.strftime("%Y-%m-%d %H:%M:%S")
