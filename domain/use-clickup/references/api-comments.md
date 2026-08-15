# ClickUp API — Comments (REWRITTEN from live audit, 2026-08-15)

> All VERIFIED live on Free Forever.

## Task comments — WORKING

- `GET /api/v2/task/{task_id}/comment` → 200
- `POST /api/v2/task/{task_id}/comment` body `{"comment_text": "..."}` → 200
- `GET /api/v2/list/{list_id}/comment` → 200 (read-only)
- **`DELETE /api/v2/comment/{comment_id}` → 200 — UNDOCUMENTED but the working delete path** (old reference's delete route was missing).

## List comments — BROKEN

- `POST /api/v2/list/{list_id}/comment` → **500 ERROR_HANDLER** (server error, no payload accepted).
Use task comments instead.

## Usage in the protocol

- Claim comment: `Claimed by <hand> — <plan>` as the first task comment (the claim lock).
- Evidence comments at milestones and at Review (the accept artifact context).

## Quirks

- Comment objects: `id`, `comment_text`, `user` (always the key's user), `date_created`, `resolved`.
