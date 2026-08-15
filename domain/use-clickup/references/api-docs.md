# ClickUp API — Docs (v3) (REWRITTEN from live audit, 2026-08-15)

> All VERIFIED live on Free Forever. Base: `https://api.clickup.com/api/v3`. Workspace id = team id `90132304521`.

## The core truth: docs are CREATE-AND-READ-ONLY at the doc level

ClickUp's own v3 spec enumerates 17 delete endpoints; **"Delete a Doc" and "Update a Doc" do not exist** (verified against the live API: `PUT /workspaces/{id}/docs/{did}` → 405 for every body; `DELETE` → 405; `?permanent=true` → 405; archive → 404; `POST /delete` → 404). **Docs are API-undeletable by design.** Only page-level cleanup exists.

## Create Doc

`POST /api/v3/workspaces/{workspace_id}/docs` body:
```json
{
  "name": "Doc name",
  "parent": {"id": "<space_id_or_list_id_or_workspace_id>", "type": 12},
  "visibility": "PUBLIC",
  "create_page": true
}
```
- `parent.type`: 12 workspace (default) · 4 space · 6 list — all nest VERIFIED (201).
- **`visibility` MUST be PUBLIC** — `PRIVATE` → `403 EXTRA_AUTHZ_002` `can_create_private_doc` (workspace permission for the key's user; enable in settings if private docs are wanted).
- → 201 with `id`.

## List / Get Docs

- `GET /api/v3/workspaces/{id}/docs` → 200 `{"docs": [...], "next_cursor": ""}`.
- `GET /api/v3/workspaces/{id}/docs/{doc_id}` → 200. **NO `pages` array** in the response (old reference wrong).

## Pages — FULL CRUD (the working surface)

- `GET /workspaces/{id}/docs/{did}/pages` → **bare JSON array** (not `{"pages": [...]}`).
- `POST /workspaces/{id}/docs/{did}/pages` body `{"name": "...", "content": "<markdown>"}` → 201. Markdown preserved (headings, bold, checkboxes, code fences VERIFIED).
- `GET /workspaces/{id}/docs/{did}/pages/{page_id}` → 200, markdown intact.
- `PUT /workspaces/{id}/docs/{did}/pages/{page_id}` → 200 — name + content mutate (VERIFIED).
- `DELETE /workspaces/{id}/docs/{did}/pages/{page_id}` → **204 — the ONLY cleanup lever.**

## Update / Delete Doc — DO NOT EXIST (405/404, verified all variants)

Housekeeping rule for artifacts: docs are append-only at doc level; update or delete PAGES; a stale doc is either page-updated or left to the UI trash (UI can delete docs).

## Quirks

- Doc ids look like `2ky4vmm9-593`; page ids like `2ky4vmm9-79`.
- Free-tier storage: 60MB total workspace storage (docs count toward it).
