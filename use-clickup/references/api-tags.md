# ClickUp Tags API

## Tag Overview

Tags are simple string labels applied to tasks. They are **not** independent resources in the ClickUp API — there is no CRUD for tags themselves. Tags are managed through task payloads:

- **Create/Update task:** Include `"tags": ["tag1", "tag2"]` to set tags
- **Search tasks:** Use `?tags[]=tag1&tags[]=tag2` query params on `GET /tasks`
- **Read tags:** Task response objects include a `"tags": [...]` array

## Space Tags

Tags are enabled/disabled per space via the space settings. Tags applied to a task must be valid for that task's space.

## Tag Format

- Case-insensitive string matching
- Spaces are allowed: `"my tag"`
- Tags replace entirely on update (not additive)

## Get Space Tags

`GET /space/{space_id}/tag`

Returns all tags configured in a space.

**Response:**
```json
{
  "tags": [
    {
      "name": "backend",
      "tag_fg": "#ffffff",
      "tag_bg": "#6bc950",
      "creator": 183
    }
  ]
}
```

## Create Space Tag

`POST /space/{space_id}/tag`

Creates a new tag in a space.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tag` | object | Yes | `{ "name": "tag_name", "tag_bg": "#color", "tag_fg": "#color" }` |
