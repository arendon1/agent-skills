# ClickUp User API

## Get Authenticated User

`GET /user`

Returns the user associated with the current API token. Useful for verifying
authentication and getting the user's workspace memberships.

**Response (200):**
```json
{
  "user": {
    "id": 162143192,
    "username": "Andrés Rendón",
    "email": "afrendonh@gmail.com",
    "color": null,
    "profilePicture": "https://attachments.clickup.com/profilePictures/...",
    "initials": "AR",
    "week_start_day": 1,
    "global_font_support": null,
    "timezone": "America/Bogota"
  }
}
```

**Python usage:**
```python
from client import get_client

client = get_client()
resp = client.get("/user")
user = resp.json()["user"]
print(f"Authenticated as {user['username']} ({user['email']})")
```

## Get User Details

`GET /team/{team_id}/user/{user_id}`

Returns a user's details within a specific team/workspace.

**Response (200):** User object with role, custom_role, last_active, date_joined.
