# ClickUp API — Chat (v3) (REWRITTEN from live audit, 2026-08-15)

> All VERIFIED live on Free Forever. Chat is NOT blocked on the free plan.
> Base: `https://api.clickup.com/api/v3`. Workspace id = team id `90132304521`.

## Working endpoints (VERIFIED)

- `GET /api/v3/workspaces/{id}/chat/channels` → 200
- `POST /api/v3/workspaces/{id}/chat/channels` → 201 (create channel)
- `GET /api/v3/workspaces/{id}/chat/channels/{channel_id}/messages` → 200
- `POST /api/v3/workspaces/{id}/chat/channels/{channel_id}/messages` → 201
- `DELETE /workspaces/{id}/chat/channels/{channel_id}` → 204
- `DELETE /workspaces/{id}/chat/channels/{channel_id}/messages/{message_id}` → 204

## Broken (VERIFIED)

- `POST /api/v3/workspaces/{id}/chat/channels/location` → 400 under every body shape — reference schema is wrong/unresolved.

## Notes

- Response shapes: channel/message objects carry `id`, `name`, `date_created`, etc. — the old reference's shape claims are off (bare arrays in some lists).
- Relevance: a future "talk to the board" channel (steering) could ride on this — but it is NOT part of the current design. Noted, not built.
