---
name: clickup-manager
description: >-
  Allows LLM agents to manage ClickUp projects using a Hybrid API approach (v3 with v2 fallback).
  Optimized for ClickUp 3.0, including Rate Limiting with visual monitoring and Free Tier enhancement.
metadata:
  version: "2.0.0"
  language: en
---

# ClickUp Manager

Allows LLM agents to manage ClickUp projects by interacting with the ClickUp API (v3/v2).

## 🔑 Authentication setup

To use this skill, you must have a ClickUp Personal Access Token (PAT).

1. **Get your PAT**:
   - Go to ClickUp Settings -> Apps -> Generate API Token.
2. **Set environment variable**:
   - Add `CLICKUP_PAT=pk_your_token_here` to your `.env` file.
3. **Install dependencies**:
   - Run `pip install -r requirements.txt` (includes `tqdm` for RPM tracking).

## ⚡ Features (v2.0)

- **Hybrid API Layer**: Uses API v3 by default, with automatic fallback to v2 for legacy endpoints.
- **Efficiency & RPM Tracking**: Managed 100 RPM with a visual progress bar and backoff.
- **ClickUp 3.0 Ready**: Structural alignment with "Workspace" terminology.
- **Free Tier Maximized**: Support for Tags, Attachments, Dependencies, and Goals.

## 🛠️ Usage

### Quick Setup 🚀

Run the interactive wizard to set up your `.env` defaults:

```bash
python scripts/clickup_client.py configure
```

### Commands

### Workspaces & Hierarchy

```bash
python scripts/clickup_client.py list-teams        # List Workspaces
python scripts/clickup_client.py list-spaces       # List Spaces in a Workspace
python scripts/clickup_client.py list-folders      # List Folders in a Space
python scripts/clickup_client.py list-lists        # List Lists in a Folder/Space
```

### Task Management

```bash
# List tasks with filters and brief output (token efficient)
python scripts/clickup_client.py --format brief list-tasks --status "Doing" --search "Bug"

# Create task (supports DD/MM/YYYY and subtasks)
python scripts/clickup_client.py create-task --name "Title" --due-date "28/02/2026" --parent <TASK_ID>

# Update task
python scripts/clickup_client.py update-task --task-id <ID> --status "Complete" --priority 1
```

### Free Tier Enhancements (NEW)

```bash
# Tags
python scripts/clickup_client.py manage-tags list --space-id <ID>
python scripts/clickup_client.py manage-tags add --task-id <ID> --tag-name "Urgent"

# Attachments (100MB Bucket)
python scripts/clickup_client.py upload-attachment --task-id <ID> --file "report.pdf"

# Dependencies
python scripts/clickup_client.py manage-dependencies add --task-id <ID> --depends-on <OTHER_ID>

# Goals
python scripts/clickup_client.py list-goals
```

### Knowledge Management (Docs v3)

```bash
python scripts/clickup_client.py list-docs
python scripts/clickup_client.py create-doc --name "Strategy"
python scripts/clickup_client.py create-page --doc-id <ID> --name "Architecture" --content "Details..."
```

## 🛡️ Best Practices & Safety

To avoid data pollution and duplicate tasks when working alongside manual users:

### 1. Search-Before-Act (Heuristic)

Always verify existence before creating new items:

- **Tasks**: Use `list-tasks --search "Name"` or the new `--check-exists` flag.
- **Tags**: The system automatically avoids duplicate tags.
- **Subtasks**: Check the parent task's subtasks before adding more.

### 2. Tiered Caching (Transparent)

The skill uses a local cache (`.clickup_cache.json`) to speed up operations:

- **Discovery (Workspaces/Lists)**: Cached for **24 hours**.
- **Operations (Tasks/Tags)**: Cached for **2 hours**.
- **Management**:
  - Use `--bypass-cache` to force a fresh fetch from ClickUp.
  - Use `configure --clear-cache` to reset all local data.

### 3. Decision Heuristics

- If an exact match is found: **Use existing ID**.
- If a partial match is found: **Ask the USER** for confirmation.
- If no match: **Proceed with creation**.

## 📚 References

- [API Documentation](references/api.md)
