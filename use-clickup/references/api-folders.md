# ClickUp Folders API

## Create Folder

`POST /space/{space_id}/folder`

Creates a new folder in a space.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Folder name |
| `list_ids` | array | No | List IDs to associate |
| `task_ids` | array | No | Task IDs to associate |
| `order` | integer | No | Order within the space |
| `override_name` | boolean | No | Override existing folder with same name |

**Response (200):** Folder object with `id`, `name`, `order`, `space`, `lists`, `tasks`.

---

## Get Folders

`GET /space/{space_id}/folder`

Returns all folders in a space.

**Query params:** `archived` (boolean)

**Response:**
```json
{
  "folders": [
    {
      "id": "1057",
      "name": "Folder Name",
      "orderindex": 5,
      "hidden": false,
      "task_count": "20",
      "space": { "id": "789", "name": "Space Name" }
    }
  ]
}
```
