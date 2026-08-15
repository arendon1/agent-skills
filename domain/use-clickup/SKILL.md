---
name: use-clickup
description: |
  ClickUp task and list management via the official API. Use when creating or updating ClickUp tasks (due dates, statuses, assignees), searching task activities and history, creating lists, or viewing existing lists. Handles authentication, response caching, and known API quirks so agent-driven ClickUp edits land correctly.
invocation: auto
layer: domain
provides: [clickup-api]
language: en-US
metadata:
  version: "1.0.0"
  risk_tier: MEDIUM
---

# use-clickup

Skill for complete ClickUp management. Essential workflows only,
with comprehensive internal documentation in `references/` for advanced capabilities.

## API Versions

ClickUp exposes two API versions for different resource types:

| Version | Base URL | Resources |
|---------|---------|-----------|
| v2 | `api.clickup.com/api/v2` | Tasks, Lists, Folders, Spaces, Comments, Checklists, Tags, Custom Fields (blocked on Free), Goals, Webhooks |
| v3 | `api.clickup.com/api/v3` | Docs, Chat (channels, messages, reactions) |

The client routes to the correct version. Use `client.get()` for v2 resources,
`client.v3_get()` for v3 resources (Docs, Chat).

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

## Caching

All GET requests are cached automatically with endpoint-aware TTLs:

| Tier | Endpoint pattern | TTL | Reasoning |
|------|-----------------|-----|-----------|
| Static | `/user`, `/team`, `/team/{id}/space` | 30 min | Rarely changes |
| Structural | `/space/{id}`, `/folder`, `/list` endpoints | 5 min | Folder/list structure stable |
| Tasks | `/list/{id}/task`, `/team/{id}/task` | 1 min | Task lists change often |

**Cache invalidation:** Any POST, PUT, or DELETE call clears the entire cache.
Cache is stored at `use-clickup/.cache/api_cache.json` and survives across
script invocations.

## Workflows

### use-clickup create-task

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

### use-clickup update-task

**Usage:** `update-task <task_id> [--name] [--description] [--due_date] [--start_date] [--priority] [--tags] [--status]`
script: `update_task.py`

**Example:**
```
/use-clickup update-task def456 \
  --due_date 2026-02-15 \
  --priority high
```

**Note:** Custom fields cannot be updated via this workflow.

---

### use-clickup search-task

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

### use-clickup create-list

**Usage:** `create-list <folder_id> <name>`
script: `create_list.py`

**Example:**
```
/use-clickup create-list folder123 "Sprint 23 — Backend Refactor"
```

---

### use-clickup view-lists

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
| 400 | Bad request — includes OAUTH_017 (missing key), INPUT_003 (bad list id), feature blockers (FIELD_605 custom fields, CRTSK_001 bad status) | No | Fix the call |
| 401 | Invalid key, OR **nonexistent resource id** (OAUTH_027/192 — misleading) | No | Check the id; verify key only for genuine 401s |
| 403 | True permission denial — only TEAM_110 (enterprise-only) observed on Free | No | Verify plan/endpoint |
| 404 | Deleted resource (ECODE) or nonexistent route (plain text) | No | Verify ID / route |
| 405 | Method not allowed — endpoint exists without that method (doc PUT/DELETE, GET /webhook/{id}) | No | Use a working method |
| 429 | Rate limit ~100/min PER KEY shared across devices (APP_002) | **Yes** | Sleep Retry-After (60s), retry |
| 500 | Server error or known broken endpoints (order_by=closed, list comments) | 5xx only | Retry 3x w/ backoff |

> Full model: `references/error-handling.md`. Note: no 409 observed on this API.

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
| `api-webhooks.md` | Webhooks (NEW — verified working on Free, URL allowlist) | `POST /team/{id}/webhook`, `GET/PUT/DELETE /webhook/{id}` |
| `api-limits-free-tier.md` | Free Forever limits & capabilities (NEW — verified) | 5 spaces · 40 lists/space · 60MB · rate limit |
| `api-chat.md` | Chat channels, messages, reactions (v3) | `GET /workspaces/{id}/chat/channels`, `POST .../messages`, `POST .../replies` |
| `api-docs.md` | Docs & pages (v3) | `GET /workspaces/{id}/docs`, `POST .../docs`, `GET .../pages` |

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
| **Custom fields are impossible on Free Forever** | `api-custom-fields.md` | FIELD_605 — the design uses zero custom fields (claim via comment) |
| **Global text search does not exist** | `api-tasks.md` | `/api/v2/task?query=` → 404; search-first = `GET /team/{id}/task` + client-side keyword match |
| **List status CRUD routes are dead** | `api-lists.md` | Set statuses via `PUT /list/{id}` with `override_statuses:true` + full statuses array (only working path) |
| **`PUT /task/{id}` with `tags` is a total no-op** | `api-tasks.md`, `api-tags.md` | Add/remove via `POST/DELETE /task/{id}/tag/{name}` — which ALSO auto-creates space tags ("must pre-exist" is wrong) |
| **Rate limit ~100/min PER KEY, shared across devices** | `error-handling.md` | 429 APP_002 + Retry-After 60; pollers must stay under budget; client now sleeps Retry-After |
| **401 OAUTH_027/192 = bad resource id, not bad key** | `error-handling.md` | Check the id first; only genuine 401s mean key problems |
| `statuses[]=Complete` returns closed tasks even without `include_closed` | `api-tasks.md` | Explicit closed-status filter overrides hidden-by-default |
| `order_by=closed` returns 500 (ITEMV2_003); `limit`/`query` silently ignored | `api-tasks.md` | Sort client-side; don't rely on limit/query |
| Docs are create-and-read-only at doc level (no update/delete endpoints — by design) | `api-docs.md` | Pages are full CRUD; update/delete pages, trash docs in UI |
| Webhooks work on Free but endpoint URL must be on an allowlisted public domain | `api-webhooks.md` | trycloudflare/quick tunnels rejected (OAUTH_194); needs fixed domain (ts.net untested) |
| `Authorization: Bearer <token>` fails for PATs | `client.py` | Use raw token without Bearer prefix: `Authorization: <token>` |
| `markdown_description=True` flattens markdown | `client.py` scripts | Send descriptions as plain `description` (`markdown_description=False`) so `##` headings survive in GET |
