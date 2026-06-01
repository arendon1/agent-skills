"""
Search for tasks in ClickUp using various filters.
"""

from typing import List, Optional, Dict
from difflib import SequenceMatcher
from client import get_client, milliseconds_to_iso

def calculate_similarity(a: str, b: str) -> float:
    """Calculates similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def search_tasks(
    name: Optional[str] = None,
    tag: Optional[str] = None,
    list_id: Optional[str] = None,
    space_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict]:
    """
    Searches tasks with optional filters.

    Args:
        name: Name (or partial) to search
        tag: Filter by tag
        list_id: Filter by specific list
        space_id: Filter by space
        limit: Maximum tasks to return (default 50)

    Returns:
        List of dicts with matching tasks
    """
    client = get_client()

    # Build query params
    params = {"limit": limit}

    # ClickUp API has limited filtering on /tasks
    # For name search, we get tasks and filter client-side

    if list_id:
        endpoint = f"/list/{list_id}/task"
    elif space_id:
        # Space tasks require intermediate folder/list
        raise ValueError(
            "To filter by space, specify list_id or folder_id"
        )
    else:
        raise ValueError(
            "list_id is required for task search"
        )

    # Get tasks
    response = client.get(endpoint, params=params)

    if response.status_code != 200:
        raise RuntimeError(
            f"Error searching tasks: {response.status_code} - {response.text}"
        )

    data = response.json()
    tasks = data.get("tasks", [])

    # Filter results
    results = []

    for task in tasks:
        # Filter by name if specified
        if name:
            similarity = calculate_similarity(name, task.get("name", ""))
            if similarity < 0.6:  # Fuzzy match threshold
                continue
            task["_similarity"] = similarity

        # Filter by tag if specified
        if tag:
            task_tags = task.get("tags", [])
            if tag not in task_tags:
                continue

        results.append(task)

    # Sort by similarity if applicable
    if name:
        results.sort(key=lambda t: t.get("_similarity", 0), reverse=True)

    return results


def format_results(tasks: List[Dict]) -> str:
    """Formats a task list for display to the user."""
    if not tasks:
        return "🔍 No tasks found"

    lines = [f"🔍 {len(tasks)} task(s) found:\n"]

    for i, task in enumerate(tasks, 1):
        name = task.get("name", "Unnamed")
        similarity = task.get("_similarity")
        status = task.get("status", {}).get("status", "unknown")
        due_date = task.get("due_date")
        tags = task.get("tags", [])
        url = task.get("url", "")

        # Similarity if searched by name
        match_info = ""
        if similarity is not None:
            match_info = f" ({int(similarity * 100)}% match)"

        due_str = ""
        if due_date:
            due_str = f" | Due: {milliseconds_to_iso(due_date)}"

        tags_str = ""
        if tags:
            tags_str = f" | Tags: {tags}"

        lines.append(
            f"{i}. {name}{match_info}\n"
            f"   Status: {status}{due_str}{tags_str}\n"
            f"   🔗 {url}\n"
        )

    return "\n".join(lines)
