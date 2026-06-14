# ClickUp Custom Fields API

## Overview

Custom fields allow extended task data beyond built-in fields. Each field has a type: `short_text`, `number`, `date`, `dropdown`, `users`, `labels`, `checkbox`, `email`, `phone`, `url`, `location`, `currency`, `text`, `rating`, `formula`, `automatic_progress`, `task_relation`.

## Set Custom Field Value

`POST /task/{task_id}/field/{field_id}`

Sets the value of a custom field on a task.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `value` | varies | Yes | Value depends on field type |
| `value_options` | object | No | Type-specific options |

**Value types by field type:**
| Type | Value format |
|------|-------------|
| `short_text`, `text`, `email`, `phone`, `url` | String |
| `number`, `rating` | Number |
| `date` | Unix time in milliseconds |
| `checkbox` | Boolean `true`/`false` |
| `dropdown` | Integer (option index) |
| `users` | Array of user IDs |
| `labels` | Array of label IDs |
| `currency` | Number (value in cents) |
| `location` | `{ "lat": 40.7, "lng": -74 }` |

**Date fields** require `value_options: { "time": true }` to display time.

**Example (date with time):**
```json
{
  "value": 1667367645000,
  "value_options": { "time": true }
}
```

---

## Get Accessible Custom Fields

`GET /list/{list_id}/field`

Returns all custom fields available in a list.

**Response:**
```json
{
  "fields": [
    {
      "id": "d2ab17e0-...",
      "name": "Sprint Goal",
      "type": "short_text",
      "type_config": {},
      "required": false
    }
  ]
}
```

---

## Remove Custom Field Value

`DELETE /task/{task_id}/field/{field_id}`

Clears a custom field value from a task. Returns `204 No Content`.
