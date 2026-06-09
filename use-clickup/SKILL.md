---
name: use-clickup
description: >-
  Task and list management in ClickUp via the official API.
  Use when creating tasks, updating dates, searching activities,
  and managing lists.
language: en-US
metadata:
  version: "1.0.0"
  risk_tier: MEDIUM
---

# /use-clickup

Skill for complete ClickUp management. Essential workflows only,
with comprehensive internal documentation in `references/` for advanced capabilities.

## Authentication

script: `client.py` — shared API client for all ClickUp operations. The API key is resolved in order:
1. `.env` file in current workspace (`CLICKUP_API_KEY` variable)
2. `CLICKUP_API_KEY` environment variable
3. Clear error with instructions if not found

## Workflows

### /use-clickup create-task

**Usage:** `create-task <list_id> <name> [--description] [--due_date] [--tags] [--priority]`
script: `create_task.py`

**Example:**
```
/use-clickup create-task abc123 "Initial Test" \
  --description "## Instructions\nRun the integration suite" \
  --due_date 2026-02-01 \
  --tags backend,critical \
  --priority high
```

**Priorities:** urgent, high, normal, low

---

### /use-clickup update-task

**Usage:** `update-task <task_id> [--name] [--description] [--due_date] [--priority] [--tags]`
script: `update_task.py`

**Example:**
```
/use-clickup update-task def456 \
  --due_date 2026-02-15 \
  --priority high
```

**Note:** Custom fields cannot be updated via this workflow.

---

### /use-clickup search-task

**Usage:** `search-task [--name] [--tag] [--list_id]`
script: `search_task.py`

**Example:**
```
/use-clickup search-task --name "Backend tests" --tag backend
```

---

### /use-clickup create-list

**Usage:** `create-list <folder_id> <name>`
script: `create_list.py`

**Example:**
```
/use-clickup create-list folder123 "Sprint 23 — Backend Refactor"
```

---

### /use-clickup view-lists

**Usage:** `view-lists [--folder_id] [--space_id]`
script: `view_lists.py`

**Example:**
```
/use-clickup view-lists --folder_id folder123
```

---

## Error Handling

| Code | Meaning | Retry? | Action |
|------|---------|--------|--------|
| 200 | Success | - | Continue |
| 400 | Bad request | No | Fix input |
| 401 | Auth failed | No | Verify API key |
| 403 | No permissions | No | Verify access |
| 404 | Not found | No | Verify ID |
| 409 | Conflict | No | Resolve duplicate |
| 429 | Rate limit | Yes | Backoff 1s, 2s, 4s |
| 500 | Server error | Yes | Retry 3x |

## Internal References

Full API documentation in `references/`:
- `api-tasks.md` — All task endpoints
- `api-lists.md` — List CRUD
- `api-folders.md` — Folder CRUD
- `api-spaces.md` — Space CRUD
- `api-comments.md` — Comments
- `api-checklists.md` — Checklists
- `api-tags.md` — Tag management
- `api-custom-fields.md` — Custom fields
- `date-formatting.md` — ISO to milliseconds conversion
- `error-handling.md` — Error codes and retry strategies
