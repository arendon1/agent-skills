# ClickUp API — Folders (REWRITTEN from live audit, 2026-08-15)

> All VERIFIED live on Free Forever.

## Get Folders

`GET /api/v2/space/{space_id}/folder` → 200 — `folders[]`.
**No "hidden" folder exists on this account** (verified even in a fresh space with folderless lists) — folderless lists sit directly at space level under `GET /space/{id}/list`. The old "hidden folder" was an artifact of the deleted space.

## Get Folder

`GET /api/v2/folder/{folder_id}` → 200 — folder object with `lists[]` INLINE (verified).

## Get Folder Lists

`GET /api/v2/folder/{folder_id}/list` → 200 — `lists[]`.
The "archived folder returns empty lists" warning is **NOT testable via API**: `PUT /folder/{id} {"archived": true}` → 200 but is a **silent no-op** (`archived` stays false). Archive is UI-only.

## Create Folder

`POST /api/v2/space/{space_id}/folder` body `{"name": "..."}` → 200. Works. No 3-folder limit observed (5 created fine).

## Create List in Folder

`POST /api/v2/folder/{folder_id}/list` body `{"name": "..."}` → 200 (this is one of only two list-create routes; bare `POST /list` → 404).

## Update Folder

`PUT /api/v2/folder/{folder_id}` → 200 (name). `archived` field is a silent no-op.

## Delete Folder

`DELETE /api/v2/folder/{folder_id}` → 200 — **SOFT delete**: subsequent `GET /folder/{id}` still 200 with `"deleted": true`; disappears from listings. Delete inner lists first to fully clean.

## Quirks

- Bad folder id → `401 OAUTH_027` (looks like auth failure, it's a bad id).
- `orderindex` not `order` in folder/list objects.
