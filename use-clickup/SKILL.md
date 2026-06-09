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

script: `client.py` — shared API client for all ClickUp operations. Authentication and
team configuration are resolved from environment in order:

**API key:**
1. `.env` file in current workspace (`CLICKUP_API_KEY` variable)
2. `CLICKUP_API_KEY` environment variable
3. Clear error with instructions if not found

**Default team (optional):**
1. `.env` file in current workspace (`CLICKUP_TEAM` variable)
2. `CLICKUP_TEAM` environment variable
3. `None` — caller must specify team at runtime

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

For workspace-wide queries (no list ID needed), use the Python API directly:
```python
from search_task import search_workspace_tasks

# All tasks in the default workspace, including closed
results = search_workspace_tasks(
    team_id="90132304521",
    include_closed=True
)
# Results are auto-sorted by date_closed descending when include_closed=True
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

## References — Full API Summary

ALL ClickUp API documentation lives in `references/`. Agents MUST search these
files first before making any external lookup — they are designed to be the
canonical reference for forming API queries.

> **Canonical source:** https://developer.clickup.com/reference  
> If these references are stale (API behavior doesn't match), cross-check
> against the live docs above and update the reference files.

### Index

| File | Covers | Key endpoints |
|------|--------|--------------|
| `api-tasks.md` | Task CRUD, team-level queries, global search | `POST /list/{id}/task`, `PUT /task/{id}`, `GET /list/{id}/task`, `GET /team/{id}/task`, `GET /tasks` |
| `api-lists.md` | List CRUD (folder & folderless) | `POST /list`, `POST /space/{id}/list`, `GET /folder/{id}/list`, `GET /space/{id}/list` |
| `api-folders.md` | Folder CRUD | `POST /space/{id}/folder`, `GET /space/{id}/folder` |
| `api-spaces.md` | Space & team discovery | `GET /team/{id}/space`, `GET /team` |
| `api-comments.md` | Task & list comments | `POST /task/{id}/comment`, `GET /task/{id}/comment`, `POST /list/{id}/comment` |
| `api-checklists.md` | Checklists & items | `POST /task/{id}/checklist`, `POST /checklist/{id}/checklist_item` |
| `api-tags.md` | Space tag management | `GET /space/{id}/tag`, `POST /space/{id}/tag` |
| `api-custom-fields.md` | Task custom fields | `POST /task/{id}/field/{id}`, `GET /list/{id}/field` |
| `date-formatting.md` | Timestamps (ms), ISO conversion helpers | `iso_to_milliseconds()`, `milliseconds_to_iso()` |
| `error-handling.md` | HTTP codes, rate limits, retry strategy | Status codes 200-503, backoff logic |
| `api-user.md` | Authenticated user verification | `GET /user` |

### How to use

1. **Forming a query:** Read the relevant reference file(s). Each one documents
   request/response schemas, query params, and examples.
2. **Scripts are wrappers:** `scripts/*.py` call these endpoints. If a script
   doesn't support a parameter you need, use the raw `client.get()` / `client.post()`
   with the endpoint and payload from the reference.
3. **Unknown behavior:** Test against the live API first, then update the reference
   file so the next agent benefits from the discovery.

### Known API Quirks

These are non-obvious behaviors discovered through live testing. Every agent
MUST know these before querying:

| Quirk | Where documented | Workaround |
|-------|-----------------|------------|
| Archived folders hide their lists from `GET /folder/{id}/list` | `api-folders.md`, `api-lists.md` | Fetch folder details (`GET /folder/{id}`) — lists are embedded inline under `lists` key |
| `include_closed=true` is mandatory for closed tasks | `api-tasks.md` | Always pass `include_closed=true` when querying tasks; lists with only closed tasks appear empty otherwise. Custom statuses with type `done`/`closed` are invisible without this flag — discover them via `GET /space/{id}` → `statuses[].type` |
| Team-level `GET /team/{id}/task` ignores archived folders | `api-tasks.md` | Discover archived folders first, then query each list individually |
| `order_by=closed` returns 500 | `api-tasks.md` | Sort client-side on `date_closed` instead |
| `Authorization: Bearer <token>` fails for PATs | `client.py` | Use raw token without Bearer prefix: `Authorization: <token>` |
