# Agent Ops — Canonical Schema (agents-pm)

> Single source of truth for the shared agent project-management space.
> ClickUp holds the task state; this file holds the schema. Update this file
> whenever the space structure changes (new list, status, tag, or field).

## Discovery

- Workspace / team: `90132304521` ("Personal")
- Space: **Agent Ops** `1000270000003780`
- Default list: **General** `1000270000007301`
- Transport: `use-clickup` skill (provides `clickup-api`). Auth resolved by
  that skill: `.env` file then `CLICKUP_API_KEY` environment variable. One
  shared token — no per-agent accounts.

## Lists

| List | id | Purpose |
|---|---|---|
| General | `1000270000007301` | Default inbox — all agent-tracked work without a dedicated home |

- A list enclose a big named project or goal (~5+ related tasks). When an
  effort grows past that, create a list (use-clickup `create-list`, i.e.
  `POST /space/{space_id}/list`) and register it in the table above.
- The General list physically sits in a hidden folder (`1000270000005916`,
  name "hidden") — a UI artifact. Treat it as a space-level list: it appears
  under `GET /space/{id}/list`. The folder is not meaningful.

## Statuses (single pipeline — exact strings)

`to do` → `ready` → `in progress` → `review` → `blocked` → `complete`

| Status | Type | Meaning |
|---|---|---|
| `to do` | open | backlog, not started |
| `ready` | custom | picked for next |
| `in progress` | custom | being worked; Owner recorded |
| `review` | custom | awaiting a review pass |
| `blocked` | custom | cannot proceed; blocker commented |
| `complete` | closed | done; closes the task |

Notes:

- Statuses are list-level (`override_statuses: true`), NOT space-level — a
  space-level status query only shows `to do`/`complete`.
- Match status strings EXACTLY (lowercase) when updating:
  `update-task <id> --status "in progress"`.

## Tags

| Tag | Meaning |
|---|---|
| `skill` | skill-building work |
| `future` | deferred / long-horizon |
| `infra` | environment, deployment, tooling |
| `waiting-on-andres` | needs the operator's decision/input (highest-value) |

## Identity tags (plain names — registry)

Tags are the bare names, no prefix: every task carries ONE device tag + ONE
harness tag, set at creation by the creating agent (its own pair). The two
dimensions are told apart by membership in this registry, not by a prefix.

**Devices** (color `#0086b3`):

- `desktop`
- `macbook`
- `phone`

**Harnesses** (color `#7b68ee`):

- `pi`
- `hermes`
- `minimax-code`
- `opencode`

Rules:

- Keep this registry in sync with the space (it is the canonical list).
- A new device or harness needs its tag created in the space BEFORE tasks can
  carry it:

```json
POST /space/1000270000003780/tag
{ "tag": { "name": "phone", "tag_bg": "#0086b3", "tag_fg": "#ffffff" } }
```

## Owner field (custom field)

- **Field:** `Owner`, type `short_text`, on each list. On General it exists;
  resolve its id with `GET /list/{list_id}/field`, create if missing:
  `POST /list/{list_id}/field` body `{ "name": "Owner", "type": "short_text" }`.
- **Value format:** `<harness>@<device>` — e.g. `pi@macbook`, `opencode@desktop`, `pi@phone`.
- **Set:** `POST /task/{task_id}/field/{field_id}` body `{ "value": "pi@macbook" }`.
- **Read:** task objects expose it under the `custom_fields` array:
  `[f for f in t.get("custom_fields", []) if f.get("name") == "Owner"]`.
- The task description's first line mirrors it — `Owner: <harness>@<device>` —
  so a cold agent reads ownership from the description while the operator
  filters by the field in the app.

## API quirks (verified live)

| Quirk | Reality |
|---|---|
| Task tags apply at creation | `POST /list/{id}/task` with `tags` works — space tags must pre-exist |
| `PUT /task/{id}` with `tags` is unreliable | Existing tags are kept; new ones are silently dropped |
| Add a tag to an existing task | `POST /task/{task_id}/tag/<name>` (URL-encode special chars: `phone%2Bhome` if any) |
| Remove a tag | `DELETE /task/{task_id}/tag/<name>` |
| List-level tag endpoints | `GET/POST /list/{id}/tag` return 404 in this workspace — use space-level |
| Custom fields on tasks | Read under `custom_fields`, not `fields` |
| Filter tasks by tag | `GET /list/{id}/task?tags[]=device:phone&include_closed=true` |

## API reference

- Team `90132304521` · Space `1000270000003780` · List General `1000270000007301`
- `include_closed=true` is mandatory when querying tasks (closed tasks and
  `complete`-type statuses are invisible without it).
- The list appears under `/space/{id}/list` despite the hidden-folder artifact.
