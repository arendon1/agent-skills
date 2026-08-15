# ClickUp API — Webhooks (NEW, from live audit 2026-08-15)

> All VERIFIED live on **Free Forever** — REST API webhooks are NOT plan-gated.
> Base: `https://api.clickup.com/api/v2`.

## Create Webhook

`POST /api/v2/team/{team_id}/webhook` body:
```json
{
  "endpoint": "https://your-domain.example/webhook",  // MUST be allowlisted public HTTPS
  "events": ["taskCreated", "taskUpdated", "taskDeleted", "taskStatusUpdated", "taskPriorityUpdated"],
  "space_id": "<space_id>"     // OPTIONAL — omit for workspace-wide
}
```
→ 200 with `{id, secret, client_id, health}`. **`secret` is for HMAC signature verification** (delivery header `x-ck-signature`).

## The URL allowlist — THE real gate (VERIFIED)

| Endpoint | Result |
|---|---|
| `https://example.com/webhook` | ✅ 200 — created instantly |
| `https://example.invalid/...` | ❌ 400 `OAUTH_194` "Specified URL not allowed" |
| `https://<random>.trycloudflare.com/...` (cloudflared quick tunnel) | ❌ 400 `OAUTH_194` |

Consequences:
- **Quick tunnels are double-dead**: URL rotates on restart AND the subdomain is rejected at registration.
- Requires a **fixed public HTTPS domain on an allowlisted TLD**: Tailscale Funnel (`*.ts.net`) UNTESTED (no tunnel installed — must be tested at adoption); a home-server domain or a real domain with cloudflared named tunnel should qualify.
- Workspace-wide (no `space_id`) registration works too.

## List / Update / Delete

- `GET /api/v2/team/{team_id}/webhook` → 200 `{"webhooks": [...]}` (includes `secret`, `health.status`, `space_id`, `endpoint`, `events`).
- `PUT /api/v2/webhook/{webhook_id}` body `{"endpoint": "...", "events": [...]}` → 200 (both endpoint and events update VERIFIED; endpoint must pass allowlist).
- `DELETE /api/v2/webhook/{webhook_id}` → 200 `{}` — webhook gone from list after.
- **`GET /api/v2/webhook/{webhook_id}` → 405** — single-webhook GET route does not exist (old docs wrong). Use the team list.

## Valid events (observed)

`taskCreated` · `taskUpdated` · `taskDeleted` · `taskStatusUpdated` · `taskPriorityUpdated`

## Architecture note (events design)

Webhook push is viable on Free Forever **once a fixed allowlisted public domain exists**.
Until then, the 60s poller is the v1 wake mechanism (`09-events.md` in the design archive).
The poller and the webhook receiver share the same rules engine.
