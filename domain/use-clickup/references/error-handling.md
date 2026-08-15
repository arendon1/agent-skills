# ClickUp API — Error Handling (REWRITTEN from live audit, 2026-08-15)

> Every entry VERIFIED live on team 90132304521, Free Forever plan.
> Old error model (401=auth failed, 403=no perms, 404=not found) is **wrong for this API** — see below.

## The real error model (VERIFIED)

| Situation | Actual response |
|---|---|
| Missing Authorization header | `400 OAUTH_017` |
| Invalid/wrong key | `401` (OAUTH family) |
| Nonexistent resource id (folders, teams, spaces as team) | `401 OAUTH_027` / `OAUTH_192` "not authorized" |
| Nonexistent **list** id | `400 INPUT_003` "List ID invalid" |
| Existed-then-deleted resource | `404` + ECODE (e.g. `PROJ_006`) |
| Nonexistent route | plain-text `404 page not found` (no JSON, no ECODE) |
| Real permission denial | `403` — rare; only `TEAM_110` (enterprise-only endpoint) observed on this account |
| Rate limit | `429 APP_002` + `Retry-After: 60` |
| Status not found on task create | `400 CRTSK_001` |
| Custom fields disabled | `400 FIELD_605` "Custom Field ClickApp is not enabled in this location" |
| Webhook URL not allowlisted | `400 OAUTH_194` "Specified URL not allowed" |

## Rate limiting (VERIFIED — critical)

- **~100 requests/min PER API KEY, SHARED across all devices/sessions using the key.**
- Exhaustion → `429 APP_002` + `Retry-After: 60` seconds. Sleep that long before retry.
- Observed: 2.5s between calls insufficient during bursts; 6s safe. For scripts doing many calls, add a small sleep and/or respect 429 backoff.
- Because the budget is shared, any poller/daemon using the key must stay well under the budget (a 60s poll ≈ 1–2 calls/min is fine).

## Retry strategy (recommended)

| Status | Action |
|---|---|
| 429 | Sleep `Retry-After` (default 60s), retry up to 3x |
| 500/502/503 | Exponential backoff 1s/2s/4s, retry 3x |
| 400/401/403/404 | No retry — fix the call; treat 401-with-OAUTH_027 and 400 INPUT_003 as "bad id", not auth failure |

## HTTP code cheat-sheet (updated)

| Code | Reality on this API |
|---|---|
| 200 | Success |
| 201 | Created (docs, chat) |
| 204 | Deleted / no content |
| 400 | Bad request — including OAUTH_017 (missing key), INPUT_003 (bad list id), feature blockers (FIELD_605, CRTSK_001) |
| 401 | Invalid key, or "not authorized" on nonexistent ids (OAUTH_027/192) |
| 403 | True permission denial — TEAM_110 enterprise-only (only observed case) |
| 404 | Deleted resource (with ECODE) or nonexistent route (plain text) |
| 405 | Method not allowed — route exists but that method doesn't (docs: PUT/DELETE doc, GET /webhook/{id}) |
| 429 | Rate limit (APP_002) — back off per Retry-After |
| 500 | Server error or known broken endpoints (order_by=closed → ITEMV2_003; list comments) |
