# Agent Ops — Canonical Schema (agents-pm)

> Single source of truth for the shared agent project-management space.
> ClickUp holds the task state; this file holds the schema. Update this file
> whenever the space structure changes (new list, status, or tag).

## Discovery

- Workspace / team: `90132304521` ("Personal")
- Space: **Agent Ops** `1000270000003780`
- Default list: **General** `1000270000007301`
- Transport: `use-clickup` skill (provides `clickup-api`). Auth resolved by
  that skill: `.env` file then `CLICKUP_API_KEY` environment variable.

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

## Owner convention

When an agent claims a task:

- First line of the task description: `Owner: <agent-identity>`
- Add a comment with the start note (what + ETA).

The Owner line is the collision signal: a claimed task is worked only by its
owner. Read owners by scanning descriptions of `in progress` / `review` tasks.

## API reference

- Team `90132304521` · Space `1000270000003780` · List General `1000270000007301`
- `include_closed=true` is mandatory when querying tasks (closed tasks and
  `complete`-type statuses are invisible without it).
- The list appears under `/space/{id}/list` despite the hidden-folder artifact.
