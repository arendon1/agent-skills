# ClickUp Tasks API

## Create Task

`POST /list/{list_id}/task`

Creates a new task in a list.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Task name |
| `description` | string | No | Plain text description |
| `markdown_description` | string | No | Markdown description |
| `assignees` | array | No | User IDs to assign |
| `tags` | array | No | Tag names |
| `status` | string | No | Task status |
| `priority` | integer | No | 1=urgent, 2=high, 3=normal, 4=low |
| `due_date` | integer | No | Unix time in milliseconds |
| `due_date_time` | boolean | No | Whether due_date includes time |
| `start_date` | integer | No | Start date in milliseconds |
| `start_date_time` | boolean | No | Whether start_date includes time |
| `parent` | string | No | Parent task ID (for subtasks) |
| `time_estimate` | integer | No | Estimated time in milliseconds |
| `custom_fields` | array | No | `[{id, value}]` objects |

**Response (200):** Full task object with `id`, `name`, `url`, `list`, `status`, etc.

**Example:**
```json
{
  "name": "My Task",
  "description": "Task description",
  "tags": ["tag1"],
  "priority": 2,
  "due_date": 1678886400000
}
```

---

## Update Task

`PUT /task/{task_id}`

Updates an existing task. Only include fields you want to change.

**Request body:** Same fields as Create Task, all optional.

**Note:** Custom fields cannot be updated with this endpoint. Use the Set Custom Field Value endpoint instead.

---

## Get Tasks

`GET /list/{list_id}/task`

Returns tasks in a list.

**Query params:** `archived`, `page`, `limit`, `include_closed`, `subtasks`

---

## Get Filtered Team Tasks

`GET /team/{teamId}/tasks`

Returns tasks filtered across the workspace.

**Query params:**
| Param | Description |
|-------|-------------|
| `list_ids` | Filter by list IDs |
| `folder_ids` | Filter by folder IDs |
| `space_ids` | Filter by space IDs |
| `include_closed` | Include closed tasks |
| `subtasks` | Include subtasks |
| `order_by` | Sort field |
| `reverse` | Reverse sort |
| `page` | Page number |
| `limit` | Results per page |

---

## Search Tasks (Global)

`GET /tasks`

Search tasks across the workspace with filters.

**Query params:**
| Param | Description |
|-------|-------------|
| `tags[]` | Filter by tags |
| `assignees[]` | Filter by assignees |
| `due_date_gt` | Due date greater than (ms) |
| `due_date_lt` | Due date less than (ms) |
| `date_created_gt` | Created after (ms) |
| `date_created_lt` | Created before (ms) |
| `date_updated_gt` | Updated after (ms) |
| `date_updated_lt` | Updated before (ms) |
| `custom_fields` | Filter by custom field value |
