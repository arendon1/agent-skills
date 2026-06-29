# ClickUp Checklists API

## Create Checklist

`POST /task/{task_id}/checklist`

Creates a new checklist on a task.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Checklist name |

**Response (200):**
```json
{
  "checklist": {
    "id": "b955c4dc-...",
    "task_id": "9hz",
    "name": "My Checklist",
    "orderindex": 0,
    "resolved": 0,
    "unresolved": 0,
    "items": []
  }
}
```

---

## Create Checklist Item

`POST /checklist/{checklist_id}/checklist_item`

Adds an item to a checklist.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Item name |
| `assignee` | integer | No | Assignee user ID |

---

## Update Checklist Item

`PUT /checklist/{checklist_id}/checklist_item/{item_id}`

Updates a checklist item (e.g., mark as resolved).

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | New item name |
| `resolved` | boolean | No | Mark as resolved |
| `parent` | string | No | Parent item ID for nesting |
