# ClickUp API — Checklists (REWRITTEN from live audit, 2026-08-15)

> All VERIFIED live on Free Forever. Full lifecycle works.

## Endpoints

- `POST /api/v2/task/{task_id}/checklist` body `{"name": "..."}` → 200
- `POST /api/v2/checklist/{checklist_id}/checklist_item` body `{"name": "..."}` → 200 (also `assignee` option)
- `DELETE /api/v2/checklist/{checklist_id}/checklist_item/{item_id}` → 200
- `DELETE /api/v2/checklist/{checklist_id}` → 200

## Reading

- Checklists appear inside task objects: `GET /task/{id}` → `checklists[]` with `items[]`.
- **Item ids nest under `checklist.items[].id`** — not top-level (old reference wrong).

## Usage

Checklists are the lightweight progress tracker inside a ticket (alternative to subtasks for non-task steps).
