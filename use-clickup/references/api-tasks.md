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

> **CRITICAL — include_closed:** When tasks are in a closed/done status
> (any status with type `closed` or `done`), they are hidden
> by default. **Always pass `include_closed=true`** to see completed tasks.
> Without it, lists with only closed tasks will appear empty (`task_count: 0`).

---

## Get Filtered Team Tasks

`GET /team/{team_id}/task`

Returns tasks filtered across the workspace. This is the recommended endpoint
for cross-list queries when you don't have a specific list ID.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `list_ids[]` | array | Filter by list IDs |
| `folder_ids[]` | array | Filter by folder IDs |
| `space_ids[]` | array | Filter by space IDs |
| `include_closed` | boolean | Include closed/completed tasks |
| `subtasks` | boolean | Include subtasks |
| `order_by` | string | Sort field: `created`, `updated`. Note: `closed` returns 500 — sort client-side instead. |
| `reverse` | boolean | Reverse sort order |
| `page` | integer | Page number (0-indexed) |
| `limit` | integer | Results per page |

**Python usage:**
```python
from search_task import search_workspace_tasks

tasks = search_workspace_tasks(
    team_id="90132304521",
    include_closed=True,
    space_ids=["901311224662"],
    limit=50
)
# Results auto-sorted by date_closed desc when include_closed=True
```

**Notes:**
- `order_by=closed` is NOT supported server-side (returns 500).
  Use client-side sorting on `date_closed` instead.
- Tasks returned include `list`, `folder`, and `space` nested objects
  with `id` and `name` fields.
- **Archived folders are invisible** to this endpoint. Tasks inside
  archived folders will NOT appear in team-level queries. To find
  them: fetch folders with `?archived=true`, get their embedded
  `lists`, then query each list directly with `include_closed=true`.

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
