# ClickUp Spaces API

## Get Spaces

`GET /team/{team_id}/space`

Returns all spaces in a workspace.

**Query params:** `archived` (boolean)

**Response:**
```json
{
  "spaces": [
    {
      "id": "5678",
      "name": "Dev Space",
      "private": false,
      "statuses": [...],
      "features": {
        "due_dates": { "enabled": true },
        "time_tracking": { "enabled": false },
        "tags": { "enabled": true }
      }
    }
  ]
}
```

---

## Get Authorized Teams (Workspaces)

`GET /team`

Returns workspaces available to the authenticated user.

**Response:**
```json
{
  "teams": [
    {
      "id": "1234",
      "name": "My Workspace"
    }
  ]
}
```
