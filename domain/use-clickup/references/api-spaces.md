# ClickUp API — Spaces (REWRITTEN from live audit, 2026-08-15)

> All VERIFIED live on Free Forever. Account has no "hidden" folder; folderless lists sit at space level.

## Get Spaces

`GET /api/v2/team/{team_id}/space` → 200 — `spaces[]` (id, name, private, statuses[], multiple_assignees, features).

## Get Space

`GET /api/v2/space/{space_id}` → 200
Includes `statuses[]` (default to do/complete), `tags` key DOES NOT exist here (tags live under `/space/{id}/tag`).

## Create Space

`POST /api/v2/team/{team_id}/space` body `{"name": "..."}` → 200
Returns id. Works on Free Forever. **Limit: 5 spaces** (free tier, official docs).

## Delete Space

`DELETE /api/v2/space/{space_id}` → 200 `{}` — HARD delete (subsequent GET → 404). Deletes all lists/tasks inside.

## Space statuses — NOT AVAILABLE VIA API (VERIFIED)

- `POST /space/{id}/status` → raw `404 page not found`
- `PUT/DELETE /space/{id}/status/{name}` → raw 404
These documented routes are **not deployed**. Status provisioning happens per-list:
`PUT /list/{id}` with `{"override_statuses": true, "statuses": [<full array>]}` (see `api-lists.md`).
Status inheritance: lists with `override_statuses:false` expose the exact space status objects.

## Space tags (the ONLY tag routes that exist)

- `GET /api/v2/space/{id}/tag` → 200
- `POST /api/v2/space/{id}/tag` body `{"tag": {"name": "...", "tag_bg": "#hex", "tag_fg": "#hex"}}` → 200
  **Colors are IGNORED on create** (defaults returned) — verified.
- `DELETE /api/v2/space/{id}/tag/{name}` → 200 — **case-insensitive** and idempotent (verified).
- List-level tag routes (`/list/{id}/tag`) → 404 — do not exist. Space tags are the way.

## Free-tier facts (verified)

- No 3-folder limit: 5 folders created in one space, all 200.
- 40 lists/space · 100 lists/folder · 100k tasks/list (official docs).

## Quirks

- Bad space id in space paths → `401 OAUTH_027` (looks like auth failure).
- `features.tags` key does not exist in space objects (old reference wrong); `orderindex` not `order`.
