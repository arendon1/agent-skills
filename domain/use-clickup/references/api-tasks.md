# ClickUp API — Tasks (REWRITTEN from live audit, 2026-08-15, 87 verified calls)

> All VERIFIED live on Free Forever. Includes search/query truth — **global text search does not exist**.

## Create Task

`POST /api/v2/list/{list_id}/task` body:
```json
{
  "name": "...",
  "description": "...",            // plain text; markdown_description flattens at write (VERIFIED)
  "status": "To Do",               // must exist on the list (400 CRTSK_001 otherwise)
  "priority": 2,                   // 1 urgent, 2 high, 3 normal, 4 low
  "tags": ["research"],            // works at creation (auto-creates space tags, VERIFIED)
  "parent": "<task_id>",           // for subtasks (2-level nesting VERIFIED)
  "assignees": [162143192],        // user id from /user
  "due_date": 1752700000000        // ms epoch
}
```
→ 200. Also accepts `markdown_description: true` but **flattens markdown into `description`** — send plain text.

## Get Tasks

- `GET /api/v2/list/{list_id}/task` → 200. Query params (all VERIFIED):
  - `include_closed=true` — closed tasks hidden WITHOUT it.
  - `statuses[]=To%20Do` OR `status=To%20Do` — both work.
  - **QUIRK: `statuses[]=Complete` returns closed tasks even WITHOUT include_closed** — an explicit closed-status filter overrides the hidden-by-default rule.
  - `tags[]=research` — works.
  - `subtasks=true` — includes subtasks in results.
  - `archived=true` — EXCLUSIVE filter (returns ONLY archived; not "include").
  - **`limit` is IGNORED** (returns everything).
  - **`query` is IGNORED** (returns everything).
- `GET /api/v2/team/{team_id}/task` → 200 — team-wide. Params (VERIFIED):
  - `include_closed=true`, `date_updated_gt=<ms>` / `date_updated_lt=<ms>` — strict ms filters, work.
  - `order_by=created|updated` — work. **`order_by=closed` → 500 `ITEMV2_003`** (confirmed broken).
  - `reverse=true`, `list_ids[]=`, `space_ids[]=`, `tags[]=research` — all work.
  - **`limit` ignored.**
- `GET /api/v2/task/{task_id}` → 200 — closed tasks fully visible here.
  - **QUIRK: `?subtasks=true` accepted but always returns empty `subtasks[]`** even for a real parented subtask (broken; use list-level `subtasks=true` instead).

## Update Task

`PUT /api/v2/task/{task_id}` — name, description, status, priority, assignees, due_date all work.
**⚠️ `tags` key in PUT is a TOTAL NO-OP** (VERIFIED: neither adds, replaces, nor clears). Add/remove tags via:
- `POST /api/v2/task/{task_id}/tag/{name}` → 200 (URL-encode special chars). **Auto-creates the space tag if missing** (VERIFIED — the "tags must pre-exist" rule is wrong).
- `DELETE /api/v2/task/{task_id}/tag/{name}` → 200 (case-insensitive).

## Delete Task

`DELETE /api/v2/task/{task_id}` → 204.

## Subtasks

- Create with `"parent": <task_id>` (2-level nesting VERIFIED — a subtask can have a subtask).
- Subtasks inherit the list's statuses.
- `GET /task/{id}` has NO `subtasks` key (parent shows no count — old reference wrong).

## Dependencies — WORK ON FREE FOREVER (VERIFIED)

- `POST /api/v2/task/{task_id}/dependency` with `depends_on` / `dependency_of` → 200. Persists (confirmed via `?include=dependencies`). Accepts even a deleted-task reference.
- Read via `GET /task/{id}?include=dependencies`.

## Time Tracking

- `POST /api/v2/team/{team_id}/time_entries` — works (VERIFIED) with `start`+`end` (ms) or `duration`+`assignee`. **`start`+`duration` alone → 400 `TIMESPENT_002`.** Free-tier status: docs say "unlimited for a limited time" (rolling trial).
- `GET /team/{id}/time_entries` → 200 (read works).
- `time_in_status` field → `400 TIS_027` (blocked).

## Attachments

`POST /api/v2/task/{task_id}/attachment` → 200 (VERIFIED).

## Custom fields on tasks — BLOCKED on Free

Setting field values is unreachable because custom fields can't be created (FIELD_605, `api-custom-fields.md`).

## Broken endpoints (do not use)

- `order_by=closed` → 500 ITEMV2_003.
- List comments (`POST /list/{id}/comment`) → 500 ERROR_HANDLER (use task comments).
- Global text search (`GET /api/v2/task?query=...`, `/task?team_id=`, `/tasks?query=`) → **404 — the endpoint does not exist.** Search-first (scoping gate) = `GET /team/{id}/task` + client-side keyword match.
