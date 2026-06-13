# ClickUp Comments API

## Create Task Comment

`POST /task/{task_id}/comment`

Adds a comment to a task.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `comment_text` | string | Yes | Comment content |
| `assignee` | integer | No | Assignee user ID |
| `notify_all` | boolean | No | Notify all watchers |
| `group_assignee` | string | No | Group ID to assign |

**Response (200):** `{ "id": "458", "hist_id": "26508", "date": 1568036964079 }`

---

## Create List Comment

`POST /list/{list_id}/comment`

Adds a comment to a list.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `comment` | string | Yes | Comment content |
| `assignees` | array | No | User IDs to assign |
| `notify_all` | boolean | No | Notify all users |
| `email` | boolean | No | Send email notification |

---

## Get Task Comments

`GET /task/{task_id}/comment`

Returns all comments on a task.

**Response:**
```json
{
  "comments": [
    {
      "id": "12345",
      "comment_text": "This is a comment.",
      "user": { "id": 183, "username": "John Doe" },
      "resolved": false,
      "date": "1568036964079",
      "reply_count": "1"
    }
  ]
}
```

---

## Get List Comments

`GET /list/{list_id}/comment`

Returns all comments on a list. Same response format as task comments.
