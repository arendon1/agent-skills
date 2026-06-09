# ClickUp Chat API (v3)

Chat channels, messages, and reactions. All endpoints use the v3 API base:
`https://api.clickup.com/api/v3`

Use `client.v3_get()`, `client.v3_post()`, etc. from `scripts/client.py`.

## List Channels

`GET /workspaces/{workspace_id}/chat/channels`

Returns all chat channels in a workspace.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `limit` | integer | Results per page (default 50) |
| `next_cursor` | string | Pagination cursor from previous response |

**Response (200):**
```json
{
  "data": [
    {
      "id": "7-90132304521-8",
      "name": "Personal",
      "type": "CHANNEL",
      "visibility": "PUBLIC",
      "archived": false,
      "is_canonical_channel": true,
      "workspace_id": "90132304521",
      "creator": "162143192",
      "created_at": 1756374867755,
      "parent": { "id": "90132304521", "type": 7 },
      "links": {
        "members": "/api/v3/workspaces/.../members",
        "followers": "/api/v3/workspaces/.../followers"
      }
    }
  ],
  "next_cursor": "..."
}
```

**Channel types:**
| Type | Meaning |
|------|---------|
| `CHANNEL` | Workspace/folder/space/list channel |
| `DM` | Direct message between users |
| `GROUP` | Group direct message |

**Parent types** (in `parent.type`):
| Value | Location |
|-------|----------|
| 4 | Space |
| 5 | Folder |
| 6 | List |
| 7 | Everything (workspace-level) |
| 12 | Workspace |

---

## Create Channel

`POST /workspaces/{workspace_id}/chat/channels`

Creates a new standalone channel.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Channel name |
| `description` | string | No | Channel description |
| `topic` | string | No | Channel topic |
| `visibility` | string | No | `PUBLIC` or `PRIVATE` (default: `PUBLIC`) |
| `user_ids` | array | No | Initial members (up to 100) |

**Response (201):** Channel object with `id`, `name`, `type`, etc.

---

## Create Location Channel

`POST /workspaces/{workspace_id}/chat/channels/location`

Creates a channel tied to a Space, Folder, or List. Returns existing channel
if one already exists at that location.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parent_id` | string | Yes | ID of the Space, Folder, or List |
| `parent_type` | number | Yes | 4=Space, 5=Folder, 6=List |
| `name` | string | No | Override default channel name |

---

## List Messages

`GET /workspaces/{workspace_id}/chat/channels/{channel_id}/messages`

Returns messages in a channel.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `limit` | integer | Results per page |
| `next_cursor` | string | Pagination cursor |

**Response (200):**
```json
{
  "data": [
    {
      "id": "msg_abc123",
      "content": "Hello world",
      "content_format": "text/md",
      "creator": "162143192",
      "created_at": 1756374867741,
      "type": "message",
      "reactions": [],
      "reply_count": 0
    }
  ],
  "next_cursor": "..."
}
```

---

## Send Message

`POST /workspaces/{workspace_id}/chat/channels/{channel_id}/messages`

Creates a new top-level message in a channel.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Message text (max 40,000 chars) |
| `content_format` | string | No | `text/md` (markdown) or `text/plain` |
| `type` | string | No | `message` or `post` |
| `assignee` | string | No | Assignee user ID |

**Response (201):**
```json
{
  "id": "msg_98765",
  "content": "Hello world",
  "creator": "162143192",
  "created_at": 1672531200000
}
```

---

## Reply to Message

`POST /workspaces/{workspace_id}/chat/messages/{message_id}/replies`

Creates a reply (thread) to an existing message.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Reply text |
| `type` | string | No | `message` or `post` |

---

## Message Reactions

### Create Reaction

`POST /workspaces/{workspace_id}/chat/messages/{message_id}/reactions`

Adds an emoji reaction to a message. Uses lowercase emoji names
(e.g., `thumbsup`, `heart`, `fire`).

### Delete Reaction

`DELETE /workspaces/{workspace_id}/chat/messages/{message_id}/reactions/{reaction_id}`

Removes a specific reaction.

---

## Channel Members & Followers

### List Members

`GET /workspaces/{workspace_id}/chat/channels/{channel_id}/members`

Returns channel members.

### Add Members

`POST /workspaces/{workspace_id}/chat/channels/{channel_id}/members`

Add users to a channel.

**Request body:** `{ "user_ids": ["user1", "user2"] }`

### List Followers

`GET /workspaces/{workspace_id}/chat/channels/{channel_id}/followers`

Returns users following the channel.

---

## Python Usage

```python
from client import get_client

client = get_client()
team_id = "90132304521"

# List channels
resp = client.v3_get(f'/workspaces/{team_id}/chat/channels')
channels = resp.json()['data']

# Send a message
resp = client.v3_post(
    f'/workspaces/{team_id}/chat/channels/{channel_id}/messages',
    json={"content": "Hello from the API!", "content_format": "text/md"}
)
message = resp.json()

# Read messages
resp = client.v3_get(
    f'/workspaces/{team_id}/chat/channels/{channel_id}/messages',
    params={"limit": 20}
)
messages = resp.json()['data']
```

## Notes

- Message content supports markdown via `"content_format": "text/md"`
- Channels on Spaces/Folders/Lists are auto-created by ClickUp as "canonical channels"
- Archived channels are still returned in list endpoints; filter by `archived` field
- DM channels have no `name` field; identify them by `type: "DM"` and member list
- The `links` object in channel responses provides URLs for members/followers sub-resources
