"""
Create a list in ClickUp via the API.
"""

from client import get_client

def create_list(
    folder_id: str,
    name: str,
    content: str = ""
) -> dict:
    """
    Creates a new list in a folder.

    Args:
        folder_id: Parent folder ID
        name: List name
        content: Initial description (optional)

    Returns:
        Dict with created list data
    """
    client = get_client()

    payload = {
        "name": name,
        "folder_id": folder_id,
        "content": content
    }

    response = client.post("/list", json=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"Error creating list: {response.status_code} - {response.text}"
        )

    return response.json()


def format_list(list_data: dict) -> str:
    """Formats a list for display to the user."""
    name = list_data.get("name", "Unnamed")
    folder = list_data.get("folder", {}).get("name", "Unknown")
    url = list_data.get("url", "")
    task_count = list_data.get("task_count", 0)

    return f"""✅ List created successfully
- Name: {name}
- Folder: {folder}
- Tasks: {task_count}
🔗 {url}"""
