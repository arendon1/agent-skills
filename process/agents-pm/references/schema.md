# Agents space — Canonical Schema (agents-pm v2)

> Single source of truth for the shared agent coordination space.
> ClickUp holds the task state; this file holds the schema. Update this file whenever
> the space structure changes (new list, status, tag, or convention).
> Rebuilt 2026-08-15 from scratch after a full API audit.

## Discovery

- Workspace / team: `90132304521` ("Personal")
- Space: **Agents** `1000270000004203` (created 2026-08-15)
- Default list: **General** `1000270000008318`
- Plan: **Free Forever** (proven via `GET /team/{id}/plan`; plan_id 13)
- Transport: `use-clickup` skill (audited 2026-08-15). Auth: `CLICKUP_API_KEY` env — one
  shared token. **Rate limit ~100 req/min PER KEY, shared across devices** (429 → APP_002,
  sleep Retry-After 60).
- **Docs feature: BANNED (core directive)** — artifacts are local files; tasks link paths.

## Lists

| List | id | Purpose |
|---|---|---|
| General | `1000270000008318` | Default inbox — all agent-tracked work without a dedicated home |

- A list encloses a big named project (~5+ related tasks). New lists via
  `POST /space/{space_id}/list` (folderless — the only list routes are folder/space-level;
  bare `POST /list` → 404) and get registered in this table.

## Statuses (single pipeline — exact LOWERCASE strings)

`backlog` → `to do` → `in progress` → `blocked` → `review` → `complete`

| Status | Type | Meaning | Set by |
|---|---|---|---|
| `backlog` | open | idea dump, not started | creator (Andrés / phone-pi) |
| `to do` | custom | RELEASED — Andrés's GO; awaiting claim | **only Andrés** |
| `in progress` | custom | claimed; ownership taken | the working hand (claim comment) |
| `blocked` | custom | cannot proceed; blocker in comment | the working hand |
| `review` | custom | done; awaiting Andrés's accept | the working hand |
| `complete` | closed | accepted; closes the task | **only Andrés** |

Notes (audited 2026-08-15):

- **ClickUp normalizes status names to lowercase on write.** Updates are case-insensitive
  (`To Do` or `to do` both work) but readbacks return the stored lowercase — ALWAYS match
  lowercase (`update-task <id> --status "in progress"`).
- Status CRUD routes are dead (`POST /list/{id}/status` → STATUS_026; space routes → 404).
  Provisioning = `PUT /list/{id}` with `{"override_statuses": true, "statuses": [<full
  array>]}` — one "open" type required, one "closed" type.
- `complete` is type `closed`; closed tasks are invisible without `include_closed=true`
  (except `statuses[]=complete` filters, which return them regardless).

## Tags — WORK-TYPE FACETS (mix-and-match, no process tags)

`research` · `build` · `analysis` · `report` · `university` · `business` · `personal` ·
`infrastructure` · `automation` · `design` · `writing` · `finance` · `content` · `learning`

Rules (Andrés's directives):

- **Full words only** — never `uni`/`infra`. Applies to every new tag.
- Tags are **facets**: any registered tag, any combination, zero to a few per task.
- Created at space level (`POST /space/{id}/tag`); colors are IGNORED on create.
- `POST /task/{id}/tag/{name}` auto-creates the space tag if missing (no need to pre-create
  — but pre-creating keeps the set deliberate).
- No process tags: no `waiting-on-andres` (review/blocked cover it), no `future`
  (backlog covers it), no `skill` (research covers it), no identity tags (the claim
  comment carries identity).

## Custom fields — NONE

Blocked on Free Forever (`FIELD_605` — Custom Fields ClickApp not enabled; dropdown also
rejected). The design uses zero custom fields by intent. Identity = the claim comment:
`Claimed by <hand> — <plan>` (also the claim lock: on collision both hands re-read and the
loser sees the other's named comment and releases).

## Description contract

```
Goal: <list> — <why this matters>

## Objective        (intent + context)
## Next steps
## Evidence Log     (chronological progress — the resume source)
## Proof of work    (filled at review — the accept artifact)
```

Tasks are **self-contained**: a cold agent must resume from the ticket alone (device-death
safety). Long-form artifacts live as local files; the description may link a local path
but never depends on it.

## API quirks (audited 2026-08-15)

| Quirk | Reality |
|---|---|
| Global text search | Does not exist (`/api/v2/task?query=` → 404) — use `GET /team/{id}/task` + client-side keyword match |
| `PUT /task/{id}` with `tags` | Total no-op — use `POST/DELETE /task/{id}/tag/{name}` |
| 401 OAUTH_027/192 | Bad resource id, NOT bad key |
| 429 APP_002 | Shared rate limit — sleep Retry-After 60 |
| Custom fields | Blocked (FIELD_605) |
| `order_by=closed` | 500 ITEMV2_003 — sort client-side |
| `limit`/`query` params | Silently ignored |
| List comments | 500 broken — use task comments |
| Docs | Create+read only, undeletable by design — banned |
| Delete list/folder | Soft delete (still resolvable by id, `deleted:true`) |

## API reference

- Team `90132304521` · Space Agents `1000270000004203` · List General `1000270000008318`
- Old (dead) ids: space `1000270000003780`, lists `1000270000008297`/`1000270000007301` —
  deleted; do not use.
- Full endpoint truth lives in the `use-clickup` skill references (audited 2026-08-15).
