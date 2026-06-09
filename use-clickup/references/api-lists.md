# ClickUp Lists API

## Create List

`POST /list`

Creates a new list in a folder or space.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | List name |
| `content` | string | No | Description |
| `folder_id` | string | No* | Parent folder ID |
| `space_id` | string | No* | Parent space ID (if no folder) |
| `priority` | integer | No | 1=urgent, 2=high, 3=normal, 4=low |
| `assignee` | integer | No | Assignee user ID |
| `due_date` | integer | No | Due date in milliseconds |
| `status` | string | No | List color |

> *Either `folder_id` or `space_id` must be provided.

**Response (200):** List object with `id`, `name`, `folder`, `space`, `statuses`, `inbound_address`.

---

## Create Folderless List

`POST /space/{space_id}/list`

Creates a list directly in a space without a folder.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | List name |
| `content` | string | No | Description |

---

## Get Lists

`GET /folder/{folder_id}/list`

Returns all lists in a folder.

> **WARNING:** When the parent folder is archived, this endpoint returns an
> empty array even though lists exist. Use `GET /folder/{id}` and read the
> `lists` key from the folder response instead.

---

## Get Folderless Lists

`GET /space/{space_id}/list`

Returns lists directly in a space (not in folders). Pass `?archived=true`
to include archived lists.

**Response:** `{ "lists": [...] }`
