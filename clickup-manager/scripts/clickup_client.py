import os
import sys
import json
import requests
import argparse
from datetime import datetime
from pathlib import Path

# Load .env file manually (Workspace > Skill Root)
def load_env(path):
    if path.exists():
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# 1. Skill Root .env (Defaults)
skill_env = Path(__file__).resolve().parent.parent / '.env'
load_env(skill_env)

# 2. Workspace/CWD .env (Overrides)
cwd_env = Path.cwd() / '.env'
if cwd_env.resolve() != skill_env.resolve(): # Avoid double loading if running from skill root
    load_env(cwd_env)

# Verify API Token
API_TOKEN = os.getenv("CLICKUP_PAT")
if not API_TOKEN:
    print("Error: CLICKUP_PAT environment variable not set.")
    sys.exit(1)


BASE_URL = "https://api.clickup.com/api/v2"
BASE_URL_V3 = "https://api.clickup.com/api/v3"
HEADERS = {
    "Authorization": API_TOKEN,
    "Content-Type": "application/json"
}

def format_output(data, format_type):
    """Format output based on request."""
    if format_type == 'brief':
        if isinstance(data, list):
            # Try to find name/id/status in common list items
            summary = []
            for item in data:
                entry = f"ID: {item.get('id', '?')} | Nombre: {item.get('name', 'Desconocido')}"
                if 'status' in item:
                    status_val = item['status'].get('status') if isinstance(item['status'], dict) else item['status']
                    entry += f" | Estado: {status_val}"
                summary.append(entry)
            print("\n".join(summary))
        elif isinstance(data, dict):
            entry = f"ID: {data.get('id', '?')} | Nombre: {data.get('name', 'Desconocido')}"
            if 'status' in data:
                status_val = data['status'].get('status') if isinstance(data['status'], dict) else data['status']
                entry += f" | Estado: {status_val}"
            print(entry)
    else:
        print(json.dumps(data, indent=2))

def list_teams(args):
    """Get Authorized Teams (Workspaces)"""
    url = f"{BASE_URL}/team"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json().get('teams', []), args.format)
    else:
        print(f"Error fetching teams: {response.status_code} - {response.text}")

def list_spaces(args):
    """Get Spaces in a Workspace"""
    url = f"{BASE_URL}/team/{args.team_id}/space?archived=false"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json().get('spaces', []), args.format)
    else:
        print(f"Error fetching spaces: {response.status_code} - {response.text}")

def list_folders(args):
    """Get Folders in a Space"""
    url = f"{BASE_URL}/space/{args.space_id}/folder?archived=false"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json().get('folders', []), args.format)
    else:
        print(f"Error fetching folders: {response.status_code} - {response.text}")

def list_lists(args):
    """Get Lists in a Folder or Space (folderless)"""
    if args.folder_id:
        url = f"{BASE_URL}/folder/{args.folder_id}/list?archived=false"
    elif args.space_id:
        url = f"{BASE_URL}/space/{args.space_id}/list?archived=false"
    else:
        print("Error: Either --folder-id or --space-id must be provided.")
        return

    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json().get('lists', []), args.format)
    else:
        print(f"Error fetching lists: {response.status_code} - {response.text}")

def list_tasks(args):
    """Get Tasks in a List with filtering"""
    url = f"{BASE_URL}/list/{args.list_id}/task?archived=false"
    
    # Add filters
    if args.status:
        url += f"&statuses[]={args.status}"
    if args.assignee:
        url += f"&assignees[]={args.assignee}"
    # Note: Search is not always available on list view locally, so we might filter client side if needed
    # But ClickUp API v2 supports some filters. We'll implement basic client-side filtering for search
    # to be robust across plans.
    
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        tasks = response.json().get('tasks', [])
        
        # Client-side filtering for search/description
        if args.search:
            search_term = args.search.lower()
            tasks = [
                t for t in tasks 
                if search_term in t.get('name', '').lower() or 
                   search_term in t.get('description', '').lower()
            ]
            
        format_output(tasks, args.format)
    else:
        print(f"Error fetching tasks: {response.status_code} - {response.text}")

def get_task(args):
    """Get specific task details"""
    url = f"{BASE_URL}/task/{args.task_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json(), args.format)
    else:
        print(f"Error fetching task: {response.status_code} - {response.text}")

def create_task(args):
    """Create a Task in a List"""
    url = f"{BASE_URL}/list/{args.list_id}/task"
    payload = {
        "name": args.name,
        "description": args.description
    }
    if args.start_date:
        payload["start_date"] = int(args.start_date)
        payload["start_date_time"] = True
    if args.due_date:
        payload["due_date"] = int(args.due_date)
        payload["due_date_time"] = True
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json(), args.format)
    else:
        print(f"Error creating task: {response.status_code} - {response.text}")

def create_list(args):
    """Create a List in a Folder or Space"""
    if args.folder_id:
        url = f"{BASE_URL}/folder/{args.folder_id}/list"
    elif args.space_id:
        url = f"{BASE_URL}/space/{args.space_id}/list"
    else:
        print("Error: Either --folder-id or --space-id must be provided.")
        return

    payload = {"name": args.name}
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json(), args.format)
    else:
        print(f"Error creating list: {response.status_code} - {response.text}")

def update_status(args):
    """Update Task Status"""
    url = f"{BASE_URL}/task/{args.task_id}"
    payload = {"status": args.status}
    response = requests.put(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json(), args.format)
    else:
        print(f"Error updating status: {response.status_code} - {response.text}")

def post_comment(args):
    """Post a comment on a task"""
    url = f"{BASE_URL}/task/{args.task_id}/comment"
    payload = {"comment_text": args.content}
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        print(f"Comentario enviado con éxito a la tarea {args.task_id}")
    else:
        print(f"Error al enviar comentario: {response.status_code} - {response.text}")

def list_members(args):
    """Get members of a list or task"""
    if args.task_id:
        url = f"{BASE_URL}/task/{args.task_id}/member"
    elif args.list_id:
        url = f"{BASE_URL}/list/{args.list_id}/member"
    else:
        print("Error: Either --list-id or --task-id must be provided.")
        return

    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json().get('members', []), args.format)
    else:
        print(f"Error fetching members: {response.status_code} - {response.text}")

def list_custom_fields(args):
    """List custom fields for a list"""
    url = f"{BASE_URL}/list/{args.list_id}/field"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json().get('fields', []), args.format)
    else:
        print(f"Error fetching custom fields: {response.status_code} - {response.text}")

def set_custom_field(args):
    """Set a custom field value on a task"""
    url = f"{BASE_URL}/task/{args.task_id}/field/{args.field_id}"
    # Value parsing (try JSON first for complex types)
    try:
        value = json.loads(args.value)
    except ValueError:
        value = args.value
        
    payload = {"value": value}
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        print(f"Custom field {args.field_id} set successfully on task {args.task_id}")
    else:
        print(f"Error setting custom field: {response.status_code} - {response.text}")

def add_time_entry(args):
    """Add a time entry to a task or team"""
    url = f"{BASE_URL}/team/{args.team_id}/time_entries"
    
    # Use current time if start not provided (milliseconds)
    start = int(args.start) if args.start else int(datetime.now().timestamp() * 1000)
    
    payload = {
        "description": args.description,
        "start": start,
        "duration": int(args.duration_ms),
        "tid": args.task_id
    }
    
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        print(f"Time entry added successfully to task {args.task_id}")
    else:
        print(f"Error adding time entry: {response.status_code} - {response.text}")

def manage_checklist(args):
    """Create or add items to checklists"""
    if args.action == "create":
        url = f"{BASE_URL}/task/{args.task_id}/checklist"
        payload = {"name": args.name}
        response = requests.post(url, json=payload, headers=HEADERS)
    elif args.action == "add-item":
        url = f"{BASE_URL}/checklist/{args.checklist_id}/checklist_item"
        payload = {"name": args.name, "assignee": args.assignee}
        response = requests.post(url, json=payload, headers=HEADERS)
    else:
        print(f"Unknown action: {args.action}")
        return

    if response.status_code == 200:
        print(f"Checklist action '{args.action}' completed successfully.")
        format_output(response.json(), args.format)
    else:
        print(f"Error managing checklist: {response.status_code} - {response.text}")

def update_task(args):
    """Update general task properties (name, description, priority, etc)"""
    url = f"{BASE_URL}/task/{args.task_id}"
    payload = {}
    if args.name: payload["name"] = args.name
    if args.description: payload["description"] = args.description
    if args.priority: payload["priority"] = int(args.priority)
    if args.status: payload["status"] = args.status
    if args.start_date:
        payload["start_date"] = int(args.start_date)
        payload["start_date_time"] = True
    if args.due_date:
        payload["due_date"] = int(args.due_date)
        payload["due_date_time"] = True
    
    if not payload:
        print("Error: No updates provided. Use --name, --description, --priority, etc.")
        return

    response = requests.put(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        print(f"Task {args.task_id} updated successfully.")
        format_output(response.json(), args.format)
    else:
        print(f"Error updating task: {response.status_code} - {response.text}")

# --- Docs (API v3) ---

def list_docs(args):
    """List Docs in a workspace"""
    url = f"{BASE_URL_V3}/workspaces/{args.team_id}/docs"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json().get('docs', []), args.format)
    else:
        print(f"Error fetching docs: {response.status_code} - {response.text}")

def create_doc(args):
    """Create a Doc in a workspace"""
    url = f"{BASE_URL_V3}/workspaces/{args.team_id}/docs"
    payload = {"name": args.name}
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 201 or response.status_code == 200:
        print(f"Documento creado con éxito.")
        format_output(response.json().get('doc', response.json()), args.format)
    else:
        print(f"Error al crear documento: {response.status_code} - {response.text}")

def create_page(args):
    """Create a page in a Doc"""
    url = f"{BASE_URL_V3}/workspaces/{args.team_id}/docs/{args.doc_id}/pages"
    payload = {
        "name": args.name,
        "content": args.content,
        "content_format": args.content_format or "text"
    }
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 201 or response.status_code == 200:
        print(f"Page created successfully in doc {args.doc_id}")
        format_output(response.json(), args.format)
    else:
        print(f"Error creating page: {response.status_code} - {response.text}")

def update_page(args):
    """Update a page's content or name"""
    url = f"{BASE_URL_V3}/workspaces/{args.team_id}/docs/{args.doc_id}/pages/{args.page_id}"
    payload = {}
    if args.name: payload["name"] = args.name
    if args.content: 
        payload["content"] = args.content
        payload["content_format"] = args.content_format or "text"
        payload["content_edit_mode"] = args.edit_mode or "replace"
        
    response = requests.put(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        print(f"Page {args.page_id} updated successfully.")
        format_output(response.json(), args.format)
    else:
        print(f"Error updating page: {response.status_code} - {response.text}")

# --- Webhooks (API v2) ---

def list_webhooks(args):
    """List webhooks for a workspace"""
    url = f"{BASE_URL}/team/{args.team_id}/webhook"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        format_output(response.json().get('webhooks', []), args.format)
    else:
        print(f"Error fetching webhooks: {response.status_code} - {response.text}")

def create_webhook(args):
    """Create a new webhook"""
    url = f"{BASE_URL}/team/{args.team_id}/webhook"
    # Events should be comma separated list in CLI
    events = [e.strip() for e in args.events.split(',')]
    payload = {
        "endpoint": args.endpoint,
        "events": events
    }
    if args.space_id: payload["space_id"] = int(args.space_id)
    if args.folder_id: payload["folder_id"] = int(args.folder_id)
    if args.list_id: payload["list_id"] = int(args.list_id)

    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        print("Webhook created successfully.")
        format_output(response.json(), args.format)
    else:
        print(f"Error creating webhook: {response.status_code} - {response.text}")

def delete_webhook(args):
    """Delete a webhook"""
    url = f"{BASE_URL}/webhook/{args.webhook_id}"
    response = requests.delete(url, headers=HEADERS)
    if response.status_code == 200:
        print(f"Webhook {args.webhook_id} deleted successfully.")
    else:
        print(f"Error deleting webhook: {response.status_code} - {response.text}")

def update_env_file(path, key, value):
    """Update or add a key-value pair in the .env file."""
    lines = []
    if path.exists():
        with open(path, 'r') as f:
            lines = f.readlines()
    
    key_found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            key_found = True
        else:
            new_lines.append(line)
    
    if not key_found:
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        new_lines.append(f"{key}={value}\n")
    
    with open(path, 'w') as f:
        f.writelines(new_lines)
    print(f"Updated {key} in {path}")

def select_item(items, item_type, optional=False):
    """Interactive selection from a list."""
    if not items:
        print(f"No {item_type}s found.")
        return None

    print(f"\nAvailable {item_type}s:")
    for i, item in enumerate(items):
        print(f"{i + 1}. {item.get('name')} (ID: {item.get('id')})")
    
    while True:
        prompt = f"Select {item_type} (1-{len(items)})"
        if optional:
            prompt += " or press Enter to skip"
        prompt += ": "
        
        choice = input(prompt)
        if optional and not choice.strip():
            return None
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(items):
                return items[index]
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")

def configure_context(args):
    """Interactive wizard to set up context."""
    # Determine .env path (prioritize CWD)
    target_env = Path.cwd() / '.env'
    
    # If arguments are provided, perform non-interactive update
    if any([args.team_id, args.space_id, args.folder_id, args.list_id]):
        print(f"Non-interactive configuration 🧙\nUpdating: {target_env}\n")
        if args.team_id:
            update_env_file(target_env, "CLICKUP_TEAM_ID", args.team_id)
        if args.space_id:
            update_env_file(target_env, "CLICKUP_SPACE_ID", args.space_id)
        if args.folder_id:
            update_env_file(target_env, "CLICKUP_FOLDER_ID", args.folder_id)
        if args.list_id:
            update_env_file(target_env, "CLICKUP_LIST_ID", args.list_id)
        print("\nConfiguration updated! 🚀")
        return

    print(f"Configuration Wizard 🧙\nSaving to: {target_env}\n")

    # 1. Select Team
    url = f"{BASE_URL}/team"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"Error fetching teams: {resp.text}")
        return
    
    team = select_item(resp.json().get('teams', []), "Team")
    if not team:
        return
    
    update_env_file(target_env, "CLICKUP_TEAM_ID", team['id'])
    
    # 2. Select Space
    url = f"{BASE_URL}/team/{team['id']}/space"
    resp = requests.get(url, headers=HEADERS)
    space = select_item(resp.json().get('spaces', []), "Space")
    if space:
        update_env_file(target_env, "CLICKUP_SPACE_ID", space['id'])
        
        # 3. Select Folder (Optional)
        url = f"{BASE_URL}/space/{space['id']}/folder"
        resp = requests.get(url, headers=HEADERS)
        folder = select_item(resp.json().get('folders', []), "Folder", optional=True)
        if folder:
            update_env_file(target_env, "CLICKUP_FOLDER_ID", folder['id'])
            
            # 4. Select List (Optional) from Folder
            url = f"{BASE_URL}/folder/{folder['id']}/list"
            resp = requests.get(url, headers=HEADERS)
            lst = select_item(resp.json().get('lists', []), "List", optional=True)
            if lst:
                update_env_file(target_env, "CLICKUP_LIST_ID", lst['id'])
        else:
            # If no folder selected, maybe they have lists directly in space (Folderless lists)
            print("Checking for folderless lists in space...")
            url = f"{BASE_URL}/space/{space['id']}/list"
            resp = requests.get(url, headers=HEADERS)
            lst = select_item(resp.json().get('lists', []), "List", optional=True)
            if lst:
                update_env_file(target_env, "CLICKUP_LIST_ID", lst['id'])

    print("\nConfiguration complete! 🚀")

def main():
    parser = argparse.ArgumentParser(description="ClickUp Manager CLI - Token Efficient")
    parser.add_argument("--format", choices=['json', 'brief'], default='brief', help="Output format (default: brief)")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to operations")

    # Configure
    config_parser = subparsers.add_parser("configure", help="Interactive setup wizard")
    config_parser.add_argument("--team-id", help="Set CLICKUP_TEAM_ID")
    config_parser.add_argument("--space-id", help="Set CLICKUP_SPACE_ID")
    config_parser.add_argument("--folder-id", help="Set CLICKUP_FOLDER_ID")
    config_parser.add_argument("--list-id", help="Set CLICKUP_LIST_ID")
    config_parser.set_defaults(func=configure_context)

    # List Teams
    teams_parser = subparsers.add_parser("list-teams", help="List all authorized workspaces (teams)")
    teams_parser.set_defaults(func=list_teams)

    # List Spaces
    spaces_parser = subparsers.add_parser("list-spaces", help="List spaces in a workspace")
    spaces_parser.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"), help="Workspace ID (Team ID). Defaults to CLICKUP_TEAM_ID.")
    spaces_parser.set_defaults(func=list_spaces)

    # List Folders
    folders_parser = subparsers.add_parser("list-folders", help="List folders in a space")
    folders_parser.add_argument("--space-id", default=os.getenv("CLICKUP_SPACE_ID"), help="Space ID. Defaults to CLICKUP_SPACE_ID.")
    folders_parser.set_defaults(func=list_folders)

    # List Lists
    lists_parser = subparsers.add_parser("list-lists", help="List lists in a folder or space")
    lists_parser.add_argument("--folder-id", default=os.getenv("CLICKUP_FOLDER_ID"), help="Folder ID. Defaults to CLICKUP_FOLDER_ID.")
    lists_parser.add_argument("--space-id", default=os.getenv("CLICKUP_SPACE_ID"), help="Space ID (for folderless lists). Defaults to CLICKUP_SPACE_ID.")
    lists_parser.set_defaults(func=list_lists)

    # List Tasks (Enhanced)
    tasks_list_parser = subparsers.add_parser("list-tasks", help="List tasks in a list")
    tasks_list_parser.add_argument("--list-id", default=os.getenv("CLICKUP_LIST_ID"), help="List ID. Defaults to CLICKUP_LIST_ID.")
    tasks_list_parser.add_argument("--status", help="Filter by status name")
    tasks_list_parser.add_argument("--assignee", help="Filter by assignee ID")
    tasks_list_parser.add_argument("--search", help="Client-side search in name/description")
    tasks_list_parser.set_defaults(func=list_tasks)

    # Get Task
    get_task_parser = subparsers.add_parser("get-task", help="Get task details")
    get_task_parser.add_argument("--task-id", required=True, help="Task ID")
    get_task_parser.set_defaults(func=get_task)

    # Create Task
    task_parser = subparsers.add_parser("create-task", help="Create a new task")
    task_parser.add_argument("--list-id", default=os.getenv("CLICKUP_LIST_ID"), help="List ID. Defaults to CLICKUP_LIST_ID.")
    task_parser.add_argument("--name", required=True, help="Task Name")
    task_parser.add_argument("--description", help="Task Description")
    task_parser.add_argument("--start-date", help="Start date in MS")
    task_parser.add_argument("--due-date", help="Due date in MS")
    task_parser.set_defaults(func=create_task)

    # Create List
    list_create_parser = subparsers.add_parser("create-list", help="Create a new list")
    list_create_parser.add_argument("--folder-id", default=os.getenv("CLICKUP_FOLDER_ID"), help="Folder ID")
    list_create_parser.add_argument("--space-id", default=os.getenv("CLICKUP_SPACE_ID"), help="Space ID (for folderless list)")
    list_create_parser.add_argument("--name", required=True, help="List Name")
    list_create_parser.set_defaults(func=create_list)

    # Update Status
    status_parser = subparsers.add_parser("update-status", help="Update task status")
    status_parser.add_argument("--task-id", required=True, help="Task ID")
    status_parser.add_argument("--status", required=True, help="New status")
    status_parser.set_defaults(func=update_status)

    # Post Comment
    comment_parser = subparsers.add_parser("post-comment", help="Post comment to task")
    comment_parser.add_argument("--task-id", required=True, help="Task ID")
    comment_parser.add_argument("--content", required=True, help="Comment text")
    comment_parser.set_defaults(func=post_comment)

    # List Members
    members_parser = subparsers.add_parser("list-members", help="List members of a list or task")
    members_parser.add_argument("--list-id", default=os.getenv("CLICKUP_LIST_ID"), help="List ID")
    members_parser.add_argument("--task-id", help="Task ID (optional, overrides list-id)")
    members_parser.set_defaults(func=list_members)

    # List Custom Fields
    cf_list_parser = subparsers.add_parser("list-custom-fields", help="List custom fields for a list")
    cf_list_parser.add_argument("--list-id", default=os.getenv("CLICKUP_LIST_ID"), help="List ID")
    cf_list_parser.set_defaults(func=list_custom_fields)

    # Set Custom Field
    cf_set_parser = subparsers.add_parser("set-custom-field", help="Set custom field value")
    cf_set_parser.add_argument("--task-id", required=True, help="Task ID")
    cf_set_parser.add_argument("--field-id", required=True, help="Field ID")
    cf_set_parser.add_argument("--value", required=True, help="Value (string or JSON for complex types)")
    cf_set_parser.set_defaults(func=set_custom_field)

    # Add Time Entry
    time_parser = subparsers.add_parser("add-time-entry", help="Add a time entry")
    time_parser.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"), help="Team/Workspace ID")
    time_parser.add_argument("--task-id", required=True, help="Task ID")
    time_parser.add_argument("--duration-ms", required=True, help="Duration in milliseconds")
    time_parser.add_argument("--description", help="Entry description")
    time_parser.add_argument("--start", help="Start time in ms (defaults to now)")
    time_parser.set_defaults(func=add_time_entry)

    # Manage Checklists
    checklist_parser = subparsers.add_parser("manage-checklist", help="Manage task checklists")
    checklist_subparsers = checklist_parser.add_subparsers(dest="action", required=True)
    
    cl_create = checklist_subparsers.add_parser("create")
    cl_create.add_argument("--task-id", required=True)
    cl_create.add_argument("--name", required=True)
    
    cl_add_item = checklist_subparsers.add_parser("add-item")
    cl_add_item.add_argument("--checklist-id", required=True)
    cl_add_item.add_argument("--name", required=True)
    cl_add_item.add_argument("--assignee", help="User ID to assign")
    
    checklist_parser.set_defaults(func=manage_checklist)

    # General Task Update
    update_task_parser = subparsers.add_parser("update-task", help="Update general task properties")
    update_task_parser.add_argument("--task-id", required=True, help="Task ID")
    update_task_parser.add_argument("--name", help="New name")
    update_task_parser.add_argument("--description", help="New description")
    update_task_parser.add_argument("--priority", help="New priority (1-4)")
    update_task_parser.add_argument("--status", help="New status")
    update_task_parser.add_argument("--start-date", help="Start date in MS")
    update_task_parser.add_argument("--due-date", help="Due date in MS")
    update_task_parser.set_defaults(func=update_task)

    # Docs Management
    doc_list_parser = subparsers.add_parser("list-docs", help="List workspace docs")
    doc_list_parser.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"), help="Workspace ID")
    doc_list_parser.set_defaults(func=list_docs)

    doc_create_parser = subparsers.add_parser("create-doc", help="Create a workspace doc")
    doc_create_parser.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"), help="Workspace ID")
    doc_create_parser.add_argument("--name", required=True, help="Doc name")
    doc_create_parser.set_defaults(func=create_doc)

    page_create_parser = subparsers.add_parser("create-page", help="Create a doc page")
    page_create_parser.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"), help="Workspace ID")
    page_create_parser.add_argument("--doc-id", required=True, help="Doc ID")
    page_create_parser.add_argument("--name", required=True, help="Page name")
    page_create_parser.add_argument("--content", help="Page content")
    page_create_parser.add_argument("--content-format", choices=['text', 'html', 'markdown'], default='text')
    page_create_parser.set_defaults(func=create_page)

    page_update_parser = subparsers.add_parser("update-page", help="Update a doc page")
    page_update_parser.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"), help="Workspace ID")
    page_update_parser.add_argument("--doc-id", required=True, help="Doc ID")
    page_update_parser.add_argument("--page-id", required=True, help="Page ID")
    page_update_parser.add_argument("--name", help="New name")
    page_update_parser.add_argument("--content", help="New content")
    page_update_parser.add_argument("--content-format", choices=['text', 'html', 'markdown'], default='text')
    page_update_parser.add_argument("--edit-mode", choices=['replace', 'append', 'prepend'], default='replace')
    page_update_parser.set_defaults(func=update_page)

    # Webhooks Management
    webhook_list_parser = subparsers.add_parser("list-webhooks", help="List workspace webhooks")
    webhook_list_parser.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"), help="Workspace ID")
    webhook_list_parser.set_defaults(func=list_webhooks)

    webhook_create_parser = subparsers.add_parser("create-webhook", help="Create a webhook")
    webhook_create_parser.add_argument("--team-id", default=os.getenv("CLICKUP_TEAM_ID"), help="Workspace ID")
    webhook_create_parser.add_argument("--endpoint", required=True, help="Destination URL")
    webhook_create_parser.add_argument("--events", required=True, help="Comma separated events (e.g. taskCreated,taskStatusUpdated)")
    webhook_create_parser.add_argument("--space-id", help="Filter by space")
    webhook_create_parser.add_argument("--folder-id", help="Filter by folder")
    webhook_create_parser.add_argument("--list-id", help="Filter by list")
    webhook_create_parser.set_defaults(func=create_webhook)

    webhook_delete_parser = subparsers.add_parser("delete-webhook", help="Delete a webhook")
    webhook_delete_parser.add_argument("--webhook-id", required=True, help="Webhook ID")
    webhook_delete_parser.set_defaults(func=delete_webhook)

    args = parser.parse_args()
    
    # Validation for required args that might rely on env vars
    # Skip validation for 'configure' command
    if args.command == "configure":
        pass
    elif args.command in ["list-spaces", "list-docs", "create-doc", "list-webhooks", "create-webhook"] and not args.team_id:
        print("Error: --team-id is required (or set CLICKUP_TEAM_ID)")
        sys.exit(1)
    elif args.command == "list-folders" and not args.space_id:
        folders_parser.error("--space-id is required (or set CLICKUP_SPACE_ID)")
    elif args.command == "list-lists" and not args.folder_id and not args.space_id:
        lists_parser.error("--folder-id or --space-id is required")
    elif (args.command in ["list-tasks", "create-task", "list-members", "list-custom-fields"]) and not args.list_id and not (hasattr(args, 'task_id') and args.task_id):
        print(f"Error: --list-id is required for {args.command} (or set CLICKUP_LIST_ID)")
        sys.exit(1)

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
