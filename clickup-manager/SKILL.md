---
name: clickup-manager
description: >-
  Manage ClickUp projects, lists, and tasks using a Personal Access Token (PAT).
  Use when you need to list workspaces, spaces, folders, lists, or create new tasks in ClickUp.
  Requires CLICKUP_PAT environment variable.
user-invocable: true
---

# ClickUp Manager

Allows LLM agents to manage ClickUp projects by interacting with the ClickUp API V2.

## 🔑 Authentication setup

To use this skill, you must have a ClickUp Personal Access Token (PAT).

1. **Get your PAT**:
    - Go to ClickUp Settings -> Apps.
    - Generate a new API Token.
2. **Set environment variable**:
    - Add `CLICKUP_PAT=pk_your_token_here` to your `.env` file.
    - **Optional - Context Scoping**: Add default IDs to avoid repeating them:

        ```bash
        CLICKUP_TEAM_ID=...
        CLICKUP_SPACE_ID=...
        CLICKUP_FOLDER_ID=...
        CLICKUP_LIST_ID=...
        ```

    - This allows you to run commands like `clickup_client.py list-tasks` without specifying the list ID every time.
    - This ensures your token is secure and not committed to git.

## ⚡ Features

- **Token Efficient**: Use `--format brief` for concise outputs.
- **Context Aware**: Auto-loads `.env` from workspace.
- **Interactive Config**: Run `configure` to set up your defaults.

## 🛠️ Usage

### Quick Setup 🚀

Type `/setup` to launch the interactive configuration wizard.

### Configuration Wizard 🧙

Run this first to interactively select your Workspace, Space, and Folder. It will save your choices to `.env`.

```bash
python scripts/clickup_client.py configure
```

### Commands

This skill provides a Python script `scripts/clickup_client.py` to interact with ClickUp.

### Efficient Data Retrieval (Brief Mode)

Use `--format brief` to save tokens by getting only IDs, names, and statuses.

```bash
python scripts/clickup_client.py --format brief list-teams
```

### List Workspaces (Teams)

```bash
python scripts/clickup_client.py list-teams
```

### List Spaces

```bash
python scripts/clickup_client.py list-spaces --team-id <TEAM_ID>
```

### List Folders

```bash
python scripts/clickup_client.py list-folders --space-id <SPACE_ID>
```

### List Lists

```bash
python scripts/clickup_client.py list-lists --folder-id <FOLDER_ID>
```

### List Tasks (with filtering)

Filter by status, assignee, or search text to find exactly what you need without loading hundreds of tasks.

```bash
# Brief list of open bugs
python scripts/clickup_client.py --format brief list-tasks --list-id <LIST_ID> --status "Open" --search "bug"
```

### Get Task Details

```bash
python scripts/clickup_client.py get-task --task-id <TASK_ID>
```

### Create Task

```bash
python scripts/clickup_client.py create-task --list-id <LIST_ID> --name "Task Name" --description "Task details"
```

### Update Status

```bash
python scripts/clickup_client.py update-status --task-id <TASK_ID> --status "in progress"
```

### Post Comment

```bash
python scripts/clickup_client.py post-comment --task-id <TASK_ID> --content "Work started on this item."
```

## 📚 References

- [API Documentation](references/api.md)
