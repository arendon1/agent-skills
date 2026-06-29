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
    Searches tasks within a specific list with optional filters.

    Args:
        name: Name (or partial) to search
        tag: Filter by tag
        list_id: Filter by specific list (required)
        space_id: Not directly supported — use search_workspace_tasks for space-level queries
        limit: Maximum tasks to return (default 50)

    Returns:
        List of dicts with matching tasks
    """
    client = get_client()

    if not list_id:
        raise ValueError(
            "list_id is required for list-level search. "
            "Use search_workspace_tasks() for team/space-level queries."
        )

    endpoint = f"/list/{list_id}/task"
    params = {"limit": limit}

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
        if name:
            similarity = calculate_similarity(name, task.get("name", ""))
            if similarity < 0.6:
                continue
            task["_similarity"] = similarity

        if tag:
            task_tags = task.get("tags", [])
            if tag not in task_tags:
                continue

        results.append(task)

    if name:
        results.sort(key=lambda t: t.get("_similarity", 0), reverse=True)

    return results


def search_workspace_tasks(
    team_id: str,
    space_ids: Optional[List[str]] = None,
    include_closed: bool = False,
    limit: int = 50,
    order_by: Optional[str] = None,
    reverse: bool = False
) -> List[Dict]:
    """
    Searches tasks across an entire workspace (team).

    Uses GET /team/{team_id}/task — the recommended endpoint for
    cross-space queries when you don't know specific list IDs.

    Args:
        team_id: ClickUp team/workspace ID (from CLICKUP_TEAM env var or explicit)
        space_ids: Optional list of space IDs to filter by
        include_closed: Include closed/completed tasks (default False)
        limit: Maximum tasks to return (default 50)
        order_by: Sort field — supported: 'created', 'updated'.
                  Note: 'closed' is NOT supported server-side; sort client-side instead.
        reverse: Reverse sort order (True = descending)

    Returns:
        List of task dicts, sorted by date_closed desc if include_closed is True
    """
    client = get_client()
    params: Dict = {"limit": limit}

    if space_ids:
        params["space_ids[]"] = space_ids
    if include_closed:
        params["include_closed"] = "true"
    if order_by and order_by != "closed":
        params["order_by"] = order_by
    if reverse:
        params["reverse"] = "true"

    endpoint = f"/team/{team_id}/task"
    response = client.get(endpoint, params=params)

    if response.status_code != 200:
        raise RuntimeError(
            f"Error searching workspace tasks: {response.status_code} - {response.text}"
        )

    data = response.json()
    tasks = data.get("tasks", [])

    # Client-side sort by closed date (server doesn't support order_by=closed)
    if include_closed:
        tasks.sort(
            key=lambda t: t.get("date_closed") or "0",
            reverse=True
        )

    return tasks


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
