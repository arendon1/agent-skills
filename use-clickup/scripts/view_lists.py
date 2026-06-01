"""
List available lists in a folder or space.
"""

from typing import Optional
from client import get_client

def view_lists(
    folder_id: Optional[str] = None,
    space_id: Optional[str] = None
) -> list:
    """
    Gets lists from a folder or space.

    Args:
        folder_id: Folder ID (takes priority over space_id)
        space_id: Space ID

    Returns:
        List of dicts with list data

    Raises:
        ValueError if neither folder_id nor space_id is provided
    """
    client = get_client()

    if folder_id:
        # Lists in a specific folder
        endpoint = f"/folder/{folder_id}/list"
    elif space_id:
        # Lists directly in a space (not in folders)
        endpoint = f"/space/{space_id}/list"
    else:
        raise ValueError(
            "You must specify folder_id or space_id"
        )

    response = client.get(endpoint)

    if response.status_code != 200:
        raise RuntimeError(
            f"Error getting lists: {response.status_code} - {response.text}"
        )

    data = response.json()
    return data.get("lists", [])


def format_lists(lists: list, context: str = "") -> str:
    """Formats lists for display to the user."""
    if not lists:
        return f"📋 No lists in {context}"

    lines = [f"📋 Lists{context}:\n"]

    for i, lst in enumerate(lists, 1):
        name = lst.get("name", "Unnamed")
        task_count = lst.get("task_count", 0)
        status = lst.get("status", {})
        # Status can be None or dict
        if status and isinstance(status, dict):
            status_name = status.get("status", "active")
        else:
            status_name = "active"

        url = lst.get("url", "")

        lines.append(
            f"{i}. {name}\n"
            f"   Tasks: {task_count} | Status: {status_name}\n"
            f"   🔗 {url}\n"
        )

    return "\n".join(lines)
