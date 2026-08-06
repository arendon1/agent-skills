# Agent Ops — ClickUp Tracking System

> External memory for agents: survives context compaction. Agents own the
> management of this space; Andrés has full read access. **ClickUp is the sole
> source of truth for task state. This file is the repo-local pointer — the
> canonical schema lives in the `agents-pm` skill
> (`process/agents-pm/references/schema.md`), whose lifecycle workflows are in
> `process/agents-pm/references/workflows.md`.**
>
> The `agents-pm` skill (process layer, auto) is the enforcement layer: it is
> consumed by all agents on all devices and is deliberately harness-agnostic.

## Discovery

- Space: **Agent Ops** id `1000270000003780` — workspace/team `90132304521` (Personal)
- Default list: **General** id `1000270000007301`
- API: `use-clickup` skill (`domain/use-clickup/scripts/client.py`), `CLICKUP_API_KEY` env
- **Convention #0 (read-side):** at session start / after compaction, query the
  `General` list before answering Andrés. Do not ask what state work is in — read it.

## Lists

Statuses encode the pipeline (Kanban); lists are reserved for enclosed,
related, highly complex efforts — a big named project or goal (when an effort
grows past ~5 related tasks, give it its own list and register it in
`process/agents-pm/references/schema.md`).

| List | id | Purpose |
|---|---|---|
| General | `1000270000007301` | Default — all agent-tracked work (formerly "Agent Tasks") |

## Statuses (single pipeline)

`to do` → `ready` → `in progress` → `review` → `blocked` → `complete` (closed)

- `to do` — backlog, not started
- `ready` — picked for next
- `in progress` — being worked; Owner recorded in the description
- `review` — waiting on a review pass (agent or human)
- `blocked` — cannot proceed; comment the blocker; add `waiting-on-andres` tag if the human must act
- `complete` — done (closed). Close in place; `include_closed=true` surfaces the archive.

## Tags

- `skill` — skill-building work
- `future` — deferred / long-horizon
- `infra` — environment, deployment, tooling
- `waiting-on-andres` — needs a decision/input from the human (highest-value query)

## Conventions

0. **Read-side:** at session start / after compaction, query the General list.
   Never rely on memory for task state.
1. Any work that could slip out of context gets a task here first. If in doubt, write it down.
2. State machine: **status encodes state, list encodes project, comment encodes evidence.**
   - Pending/future → `to do` + `future` tag. Started → `in progress` + Owner line.
   - External blocker → `blocked` + comment with the blocker + `waiting-on-andres` tag if it needs the human.
   - Needs review → `review` (waiting on a review pass), NOT `blocked` (cannot proceed).
   - Done → `complete` + closing comment.
3. Task descriptions MUST be self-contained: objective, context pointers (plan
   folders), verified facts, explicit next steps — a cold agent must resume
   without prior context.
4. Never put secrets in task descriptions, comments, or docs (repo is public).
5. Scoping gate: no non-trivial work starts until it exists as a task.

## API reference

- Team: `90132304521` · Space: `1000270000003780` · List: General `1000270000007301`
- `include_closed=true` is mandatory when querying tasks (skill reference quirk).
- The General list appears under `/space/{id}/list` despite a hidden-folder artifact.
