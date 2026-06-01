"""
Create a task in ClickUp via the API.
"""

from typing import List, Optional
from client import get_client, iso_to_milliseconds

PRIORITIES = {
    "urgent": 1,
    "high": 2,
    "normal": 3,
    "low": 4
}

def create_task(
    list_id: str,
    name: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None,
    priority: Optional[str] = None,
    markdown_description: bool = True
) -> dict:
    """
    Creates a new task in ClickUp.

    Args:
        list_id: Target list ID
        name: Task name
        description: Description (text or markdown)
        due_date: Date in ISO 8601 format (YYYY-MM-DD)
        tags: List of tags to assign (no validation, defined by the orchestrating skill)
        priority: "urgent", "high", "normal", "low"
        markdown_description: Use markdown in description

    Returns:
        Dict with created task data

    Raises:
        ValueError if priority is invalid
        RuntimeError if the API fails
    """
    client = get_client()

    # Validate priority
    if priority and priority not in PRIORITIES:
        raise ValueError(
            f"Invalid priority: '{priority}'. "
            f"Valid values: {list(PRIORITIES.keys())}"
        )

    # Build payload
    payload = {"name": name}

    if description:
        if markdown_description:
            payload["markdown_description"] = description
        else:
            payload["description"] = description

    if due_date:
        try:
            payload["due_date"] = iso_to_milliseconds(due_date)
            payload["due_date_time"] = False  # Date only, no time
        except ValueError as e:
            raise ValueError(f"Invalid date: {e}")

    if tags:
        payload["tags"] = tags

    if priority:
        payload["priority"] = PRIORITIES[priority]

    # Make request
    response = client.post(f"/list/{list_id}/task", json=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"Error creating task: {response.status_code} - {response.text}"
        )

    return response.json()


def format_task(task: dict) -> str:
    """Formats a task for display to the user."""
    name = task.get("name", "Unnamed")
    list_name = task.get("list", {}).get("name", "Unknown")
    url = task.get("url", "")
    due_date = task.get("due_date")
    tags = task.get("tags", [])

    due_date_str = ""
    if due_date:
        from client import milliseconds_to_iso
        due_date_str = f"\n   - Due: {milliseconds_to_iso(due_date)}"

    tags_str = ""
    if tags:
        tags_str = f"\n   - Tags: {tags}"

    return f"""✅ Task created successfully
- Name: {name}
- List: {list_name}{due_date_str}{tags_str}
🔗 {url}"""
