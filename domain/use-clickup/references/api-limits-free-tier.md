# ClickUp Free Forever — Limits & Capabilities (NEW, compiled 2026-08-15)

> Sources: live API probes on team 90132304521 + official ClickUp docs (feature-availability series, fetched 2026-08-15).
> Plan proven at runtime: `GET /team/{id}/plan` → `{"plan_name":"Free Forever","plan_id":13}`.

## Hard limits (official docs)

| Feature | Free Forever limit |
|---|---|
| Spaces | **5** |
| Lists per Space | **40** (newer doc; older said 100 — 40 is current) |
| Lists per Folder | **100** |
| Tasks per List | **100,000** (incl. archived + subtasks) |
| Storage (workspace) | **60MB** (not 100MB — corrected) |
| Automations | 5 active · 100 actions/mo · paused when exceeded |
| Dashboards | cannot create |
| Guests/Members | unlimited |

## Works on Free (VERIFIED via API)

- Tasks, subtasks (2-level), comments (task-level), checklists, dependencies, attachments, priorities, assignees, time tracking (write needs `start`+`end` or `duration`+assignee)
- Spaces/folders/lists CRUD · space tags · **REST API webhooks** (URL-allowlist-gated)
- Goals API (read+write) · Chat v3 (channels + messages) · Docs v3 (create + read; pages full CRUD)
- Team task queries with filters (`include_closed`, `date_updated_gt/lt`, `tags[]`, `statuses[]`, `list_ids[]`, `space_ids[]`)

## Blocked / absent on Free (VERIFIED)

| Capability | Evidence |
|---|---|
| Custom fields (create) | `400 FIELD_605` — Custom Fields ClickApp not enabled |
| `dropdown` field type | `400 FIELD_422` |
| Global text search | endpoint does not exist (404) |
| Dashboards/Automations/Templates/Rooms/Whiteboards APIs | routes do not exist (plain 404) — in-app gating |
| `time_in_status` | `400 TIS_027` |
| List comments (create) | 500 server error |
| `order_by=closed` | 500 `ITEMV2_003` |
| `limit`/`query` params on task queries | silently ignored |
| Enterprise endpoints | `403 TEAM_110` (e.g. per-user team endpoint) |
| Private docs | `403 EXTRA_AUTHZ_002` `can_create_private_doc` (workspace setting) |
| Doc update/delete | 405 — endpoints do not exist by design |

## Operational constraints (VERIFIED)

- **Rate limit ~100 req/min PER KEY, shared across all devices/sessions** using the key. 429 → `APP_002` + `Retry-After: 60`. Any daemon (poller) must stay well under budget.
- Plan detection at runtime: `GET /team/{id}/plan`.
