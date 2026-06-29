"""
Update an existing task in ClickUp via the API.
"""

from typing import Optional, List
from client import get_client, iso_to_milliseconds

def update_task(
    task_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
    markdown_description: bool = True
) -> dict:
    """
    Updates fields of an existing task.

    Args:
        task_id: ID of the task to update
        name: New name (optional)
        description: New description (optional)
        due_date: New date in ISO 8601 (optional)
        priority: New priority (optional)
        tags: New tags (replaces current ones)
        status: New status (e.g., "in progress", "complete")

    Returns:
        Dict with updated task data

    Note: Custom fields cannot be updated with PUT /tasks/{task_id}.
    Use the specific endpoint for custom fields.
    """
    client = get_client()

    # Build payload with only the fields to update
    payload = {}

    if name is not None:
        payload["name"] = name

    if description is not None:
        if markdown_description:
            payload["markdown_description"] = description
        else:
            payload["description"] = description

    if due_date is not None:
        try:
            payload["due_date"] = iso_to_milliseconds(due_date)
        except ValueError as e:
            raise ValueError(f"Invalid date: {e}")

    if priority is not None:
        PRIORITIES = {"urgent": 1, "high": 2, "normal": 3, "low": 4}
        if priority not in PRIORITIES:
            raise ValueError(f"Invalid priority: {priority}")
        payload["priority"] = PRIORITIES[priority]

    if tags is not None:
        payload["tags"] = tags

    if status is not None:
        payload["status"] = status

    if not payload:
        raise ValueError("No fields provided to update")

    # Make request
    response = client.put(f"/task/{task_id}", json=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"Error updating task: {response.status_code} - {response.text}"
        )

    return response.json()
