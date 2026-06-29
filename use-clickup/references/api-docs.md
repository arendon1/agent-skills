# ClickUp Docs API (v3)

Document management. All endpoints use the v3 API base:
`https://api.clickup.com/api/v3`

Use `client.v3_get()`, `client.v3_post()`, etc. from `scripts/client.py`.

## List Docs

`GET /workspaces/{workspace_id}/docs`

Returns all Docs in a workspace.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `limit` | integer | Results per page |
| `next_cursor` | string | Pagination cursor |

**Response (200):**
```json
{
  "docs": [
    {
      "id": "2ky4vmm9-593",
      "name": "Meeting Notes - 02/27/2026",
      "type": 3,
      "workspace_id": 90132304521,
      "creator": 162143192,
      "date_created": 1772230121875,
      "date_updated": 1772439028992,
      "parent": { "id": "90132304521", "type": 12 },
      "deleted": false
    }
  ],
  "next_cursor": ""
}
```

**Parent types** (in `parent.type`):
| Value | Location |
|-------|----------|
| 4 | Space |
| 5 | Folder |
| 6 | List |
| 7 | Everything |
| 12 | Workspace |

---

## Get Doc

`GET /workspaces/{workspace_id}/docs/{doc_id}`

Returns a single Doc with full metadata.

**Response (200):** Full Doc object including `pages` array (if pages exist).

---

## Create Doc

`POST /workspaces/{workspace_id}/docs`

Creates a new Doc.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Doc name (default: "") |
| `parent` | object | No | Parent location `{ "id": "...", "type": 12 }` |
| `visibility` | string/number | No | `"PUBLIC"` (1), `"PRIVATE"` (2), `"PERSONAL"` (3), `"HIDDEN"` (4) |
| `create_page` | boolean | No | Auto-create first page (default: true) |

**Visibility values:**
| String | Number | Description |
|--------|--------|-------------|
| `PUBLIC` | 1 | Visible to workspace |
| `PRIVATE` | 2 | Visible to invited users |
| `PERSONAL` | 3 | Only creator |
| `HIDDEN` | 4 | Hidden from listings |

**Example:**
```json
{
  "name": "Sprint Planning Notes",
  "parent": { "id": "90132304521", "type": 12 },
  "visibility": "PRIVATE",
  "create_page": true
}
```

**Response (201):** Full Doc object with `id`, `name`, `type`, `parent`, `workspace_id`, `creator`, `archived`, `deleted`, `page_defaults`.

---

## Update Doc

`PUT /workspaces/{workspace_id}/docs/{doc_id}`

Updates a Doc's metadata (name, visibility, parent).

**Request body:** Same fields as Create Doc, all optional.

---

## Delete Doc

`DELETE /workspaces/{workspace_id}/docs/{doc_id}`

Soft-deletes a Doc (moves to trash). Returns `204 No Content`.

---

## Pages

### List Pages

`GET /workspaces/{workspace_id}/docs/{doc_id}/pages`

Returns all pages within a Doc.

### Create Page

`POST /workspaces/{workspace_id}/docs/{doc_id}/pages`

Creates a new page within a Doc.

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Page name |
| `content` | string | No | Page content (rich text/markdown) |

### Get Page

`GET /workspaces/{workspace_id}/docs/{doc_id}/pages/{page_id}`

Returns a single page with its content.

### Update Page

`PUT /workspaces/{workspace_id}/docs/{doc_id}/pages/{page_id}`

Updates a page's name or content.

### Delete Page

`DELETE /workspaces/{workspace_id}/docs/{doc_id}/pages/{page_id}`

Deletes a page from a Doc.

---

## Python Usage

```python
from client import get_client

client = get_client()
team_id = "90132304521"

# List docs
resp = client.v3_get(f'/workspaces/{team_id}/docs')
docs = resp.json()['docs']

# Get a doc with pages
resp = client.v3_get(f'/workspaces/{team_id}/docs/{doc_id}')
doc = resp.json()

# List pages
resp = client.v3_get(f'/workspaces/{team_id}/docs/{doc_id}/pages')
pages = resp.json().get('pages', resp.json().get('data', []))

# Create a doc
resp = client.v3_post(
    f'/workspaces/{team_id}/docs',
    json={
        "name": "Meeting Notes",
        "parent": {"id": team_id, "type": 12},
        "visibility": "PRIVATE"
    }
)
new_doc = resp.json()
```

## Notes

- Docs are separate from Tasks — they're long-form collaborative documents
- A Doc contains pages (hierarchical content)
- Parent type `12` (Workspace) creates a workspace-level doc
- Visibility controls who can see and edit the doc
- Docs can be nested under Spaces, Folders, or Lists via `parent`
