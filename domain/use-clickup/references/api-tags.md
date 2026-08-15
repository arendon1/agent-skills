# ClickUp API — Tags (REWRITTEN from live audit, 2026-08-15)

> All VERIFIED live on Free Forever. **Space-level is the only tag home** — list-level tag routes do not exist.

## Space-level tags (THE routes)

- `GET /api/v2/space/{space_id}/tag` → 200
- `POST /api/v2/space/{space_id}/tag` body `{"tag": {"name": "research", "tag_bg": "#87909e", "tag_fg": "#ffffff"}}` → 200
  - **Colors are IGNORED on create** (VERIFIED) — tags get defaults; cosmetic only.
  - Tag names: full words only (directive), lowercase convention, case-sensitive in reads.
- `DELETE /api/v2/space/{space_id}/tag/{name}` → 200 — **case-insensitive** and idempotent (VERIFIED).

## Tags on tasks

- At creation: `POST /list/{id}/task` with `"tags": ["research"]` → 200. **Auto-creates the space tag if missing** (VERIFIED — "tags must pre-exist" is WRONG).
- Add: `POST /api/v2/task/{task_id}/tag/{name}` → 200 (URL-encode special chars). Also auto-creates.
- Remove: `DELETE /api/v2/task/{task_id}/tag/{name}` → 200 (case-insensitive).
- **`PUT /task/{id}` with `tags` is a TOTAL NO-OP** (VERIFIED — never use it).

## List-level tags — DO NOT EXIST

`GET/POST /list/{id}/tag` → raw 404. Confirmed. Use space-level.

## Filtering

- `GET /list/{id}/task?tags[]=research&include_closed=true` — works.
- `GET /team/{id}/task?tags[]=research` — works.

## Note

There is no team-level tag route (`/team/{id}/tags` → 404). Tags live per-space; a task's tags must exist in its space (auto-created on demand).
