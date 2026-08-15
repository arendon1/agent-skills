# ClickUp API — Lists & Statuses (REWRITTEN from live audit, 2026-08-15)

> All VERIFIED live on Free Forever. This file is the ONLY reliable source for status provisioning — the documented status-CRUD routes are dead.

## Create List — two working routes only

- `POST /api/v2/folder/{folder_id}/list` (folder list)
- `POST /api/v2/space/{space_id}/list` (folderless list)
- **Bare `POST /api/v2/list` → 404** (old reference wrong). The id lives in the URL, not the body.

## Get Lists

- `GET /api/v2/space/{space_id}/list` → 200 — folderless lists (the reliable listing).
- `GET /api/v2/folder/{folder_id}/list` → 200 — folder lists.
- `GET /api/v2/list/{list_id}` → 200 — full shape: `override_statuses` flag, `statuses[]` (id/status/color/type/status_group), `folder`, `space`, `permission_level`, `deleted`.

## Update List — **THE status provisioning endpoint**

`PUT /api/v2/list/{list_id}` body:
```json
{
  "name": "...",               // optional
  "override_statuses": true,   // required when setting statuses
  "statuses": [                // REQUIRED in same request when override_statuses:true
    {"status": "Backlog", "type": "open", "orderindex": 0, "color": "#87909e"},
    {"status": "To Do", "type": "custom", "orderindex": 1, "color": "#87909e"},
    {"status": "In Progress", "type": "custom", "orderindex": 2, "color": "#87909e"}
    // ... one "open"-type status REQUIRED, exactly one
  ]
}
```
- `{"override_statuses": true}` WITHOUT the array → `400 STATUS_002` "Open is a required status type and there can only be one".
- With the array → 200, `override_statuses` flips to true, statuses persisted (verified).
- **This is the ONLY working way to set list statuses.**

## List status CRUD — DEAD (VERIFIED)

- `POST /list/{id}/status` → `400 STATUS_026` "Status name is required" on EVERY payload shape (nested docs shape, flat, `{"name":...}`) — name is present in all; the route half-exists but rejects everything.
- `PUT /list/{id}/status/{name}` / `DELETE /list/{id}/status/{name}` → raw 404 (route absent).
- Space-level status routes → raw 404 (see `api-spaces.md`).
- Consequence: statuses can only be set wholesale via `PUT /list/{id}` (above). Plan the full 6-column pipeline at list creation.

## Delete List

`DELETE /api/v2/list/{list_id}` → 200 — **SOFT delete**: subsequent `GET /list/{id}` → 200 with `"deleted": true`; disappears from `GET /space/{id}/list`.

## List tags — DO NOT EXIST

`GET /list/{id}/tag` and `POST /list/{id}/tag` → raw 404. Use space-level tags (`api-spaces.md`).

## List custom fields

`GET /list/{id}/field` → 200 (`fields[]`, empty on fresh lists). **Create/delete are impossible on Free Forever**: `POST /list/{id}/field` → `400 FIELD_605` (Custom Fields ClickApp not enabled); `DELETE /field/{id}` and `/list/{id}/field/{id}` → 405 (no route). See `api-custom-fields.md`.

## Quirks

- Bad list id → `400 INPUT_003` "List ID invalid" (not 404).
- Task create with unknown status → `400 CRTSK_001` "Status not found".
