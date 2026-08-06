# Agent Ops — ClickUp Tracking System

> External memory for the agent: survives context compaction. The agent owns
> management of this space; Andrés has full read access. **This file is the
> SCHEMA only — ClickUp is the sole source of truth for task state.**

## Discovery

- Space: **Agent Ops** id `1000270000003780` — workspace/team `90132304521` (Personal)
- API: `use-clickup` skill (`domain/use-clickup/scripts/client.py`), `CLICKUP_API_KEY` env
- **Convention #0 (read-side):** at session start / after compaction, query the
  `Agent Tasks` list before answering Andrés. Do not ask what state work is in — read it.

## Lists

One default list — **statuses encode the pipeline (Kanban)**; lists are reserved
for enclosed, related, highly complex efforts (when an effort grows past ~5
related tasks, give it its own list and note it here).

| List | id | Purpose |
|---|---|---|
| Agent Tasks | `1000270000007301` | All agent-tracked work (default) |

## Statuses (single pipeline)

`to do` → `Ready` → `In Progress` → `Review` → `Blocked` → `complete` (closed)

- `to do` — backlog, not started
- `Ready` — picked for next
- `In Progress` — being worked
- `Review` — waiting on a review pass (agent or human)
- `Blocked` — cannot proceed; comment the blocker; add `waiting-on-andres` tag if the human must act
- `complete` — done (closed). Close in place; `include_closed=true` surfaces the archive.

## Tags

- `skill` — skill-building work
- `future` — deferred / long-horizon
- `infra` — environment, deployment, tooling
- `waiting-on-andres` — needs a decision/input from the human (highest-value query)

## Conventions

0. **Read-side:** at session start / after compaction, query the Agent Tasks list. Never rely on memory for task state.
1. Any work that could slip out of context gets a task here first. If in doubt, write it down.
2. State machine: **status encodes state, list encodes phase, comment encodes evidence.**
   - Pending/future → `to do` + `future` tag. Started → `In Progress`.
   - External blocker → `Blocked` + comment with the blocker + `waiting-on-andres` tag if it needs the human.
   - Needs review → `Review` (waiting on a review pass), NOT `Blocked` (cannot proceed).
   - Done → `complete` + closing comment.
3. Task descriptions MUST be self-contained: objective, context pointers (plan folders), verified facts, explicit next steps — a cold agent must resume without prior context.
4. Never put secrets in task descriptions, comments, or docs (repo is public).

## API reference

- Team: `90132304521` · Space: `1000270000003780` · List: Agent Tasks `1000270000007301`
- `include_closed=true` is mandatory when querying tasks (skill reference quirk).
