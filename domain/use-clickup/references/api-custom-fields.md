# ClickUp API — Custom Fields (REWRITTEN from live audit, 2026-08-15)

> All VERIFIED live on **Free Forever**. Bottom line: **custom fields are unusable on the free plan** — the design correctly uses zero custom fields.

## The hard blocker (VERIFIED)

- `POST /api/v2/list/{list_id}/field` body `{"name": "X", "type": "short_text"}` → **400 `FIELD_605` "A Custom Field ClickApp is not enabled in this location."**
- The Custom Fields ClickApp cannot be enabled for this space on Free Forever. No body variant works (all 4 tested).
- `dropdown` type → additionally `400 FIELD_422` "Invalid field type 'dropdown'" (documented type rejected).

## What does work

- `GET /api/v2/list/{list_id}/field` → 200 (`{"fields": []}` on fresh lists). Read side only.
- Setting/removing a value on a task (`POST /task/{id}/field/{field_id}`) exists in docs but is unreachable (no field can exist).

## Deletion — no route

- `DELETE /field/{field_id}` → 405 raw
- `DELETE /list/{list_id}/field/{field_id}` → 405 raw
No custom-field delete endpoint exists.

## Consequence for the Agent Ops design

Owner/Reviewer/Orchestrator as custom fields are impossible. The design's zero-fields stance (claim via comment, identity in the claim comment) is not minimalism — it is the plan's reality.
