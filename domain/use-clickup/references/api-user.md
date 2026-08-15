# ClickUp API — User, Team, Plan (REWRITTEN from live audit, 2026-08-15)

> All VERIFIED live on team 90132304521 (Free Forever, plan_id 13).

## Get Authenticated User

`GET /api/v2/user` → 200
Returns the key's user (id, username, email, initials, profile picture).

## Get Teams (workspaces)

`GET /api/v2/team` → 200
Returns `teams[]` with `id` and `name`. This account: `[("90132304521", "Personal")]`.

## Get Team / Workspace

`GET /api/v2/team/{team_id}` → 200
Returns the team object.

## Get Team Plan (UNDOCUMENTED but works — use for plan checks)

`GET /api/v2/team/{team_id}/plan` → 200
```json
{"plan_name": "Free Forever", "plan_id": 13}
```
This is how to PROVE the account's plan at runtime. Verified twice.

## Enterprise-only (VERIFIED blocked)

`GET /team/{team_id}/user/{user_id}` → 403 `TEAM_110` "Team must be on enterprise plan".
Do not rely on per-user endpoints.

## Rate limit

Shared ~100 req/min per key across devices (see `error-handling.md`).

## Quirks

- Bad team id in `/team/{id}*` paths → `401 OAUTH_192` "not authorized" (looks like auth failure; it's a bad id).
- No billing/plan-membership endpoints exist beyond `/plan` (billing → 404 plain text).
