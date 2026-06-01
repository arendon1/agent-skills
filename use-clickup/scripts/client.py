"""
Base HTTP client for the ClickUp API.
Handles authentication and request configuration.
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

class ClickUpClient:
    """ClickUp API client with error handling and retries."""

    BASE_URL = "https://api.clickup.com/api/v2"
    TIMEOUT = 30  # seconds
    MAX_RETRIES = 3

    def __init__(self):
        self.api_key = self._get_api_key()
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

    def _create_session(self) -> requests.Session:
        """Creates an HTTP session with common headers."""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        return session

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Executes an HTTP request with automatic retries.

        Args:
            method: GET, POST, PUT, DELETE
            endpoint: API path (e.g., /tasks)
            **kwargs: Additional arguments for requests

        Returns:
            Response from requests

        Raises:
            RuntimeError on authentication error
            requests.exceptions.RequestException if it fails after retries
        """
        url = f"{self.BASE_URL}{endpoint}"

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


# Global client instance (lazy loading)
_client: Optional[ClickUpClient] = None

def get_client() -> ClickUpClient:
    """Returns the singleton client instance."""
    global _client
    if _client is None:
        _client = ClickUpClient()
    return _client


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
