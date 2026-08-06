# agents-pm — Workflows

Exact commands for the agents-pm lifecycle. All commands run through the
`use-clickup` skill (its `scripts/` directory). Adjust the command prefix to
the local installation of that skill. `<identity>` = `<harness>@<device>`
(see `schema.md`).

## 0. Read the space (session start / after compaction)

Open + closed tasks in General, grouped by status, with owner + tags:

```python
# run from the use-clickup skill's scripts/ directory
from client import get_client
c = get_client()
tasks = c.get("/list/1000270000007301/task",
              params={"include_closed": "true"}).json()["tasks"]
for t in sorted(tasks, key=lambda x: x.get("date_updated", ""), reverse=True):
    st = t.get("status", {}).get("status")
    owner = [f["value"] for f in t.get("custom_fields", [])
             if f.get("name") == "Owner"]
    tags = [tag["name"] for tag in t.get("tags", [])]
    print(st, "|", t["name"][:55], "|", (owner[0] if owner else "-"), "|", ",".join(tags))
```

Per-device / per-harness views (answers "what is running on the phone"):

```python
r = c.get("/list/1000270000007301/task",
          params={"include_closed": "true", "tags[]": "device:phone"})
for t in r.json()["tasks"]:
    print(t.get("status", {}).get("status"), "|", t["name"][:60])
```

Or the script (open tasks only):

```bash
python search_task.py --list_id 1000270000007301
```

Group mentally by status. Surface `waiting-on-andres` tags to the operator
first, then `blocked`, then in-progress ownership (Owner field + description).

## 1. Scope before work

Search before starting — no work without a task:

```bash
python search_task.py --name "<keyword>"
```

Create a missing task with a self-contained description AND your identity
tags (they must pre-exist in the space — see `schema.md`):

```bash
python create_task.py 1000270000007301 "Short actionable title" \
  --description "## Objective\n<what and why>\n\nOwner: <identity>\n\n## Context\n<pointers>\n\n## Next steps\n1. ..." \
  --tags pi,macbook
```

## 2. Claim

```bash
python update_task.py <task_id> --status "in progress"
# Owner field + description Owner line + start comment via client:
python -c "
from client import get_client
c = get_client()
fid = next(f['id'] for f in c.get('/list/1000270000007301/field').json()['fields'] if f['name']=='Owner')
c.post(f'/task/<task_id>/field/{fid}', json={'value': '<identity>'})
c.post('/task/<task_id>/comment', json={'comment_text': 'Started by <identity>: <what + ETA>'})
"
```

If a task lacks your identity tags (e.g. pre-dating this convention), add
them without touching other tags:

```python
c.post("/task/<task_id>/tag/pi")
c.post("/task/<task_id>/tag/macbook")
```

## 3. Update (progress)

```bash
python update_task.py <task_id> --description "<refreshed, still self-contained>"
python -c "from client import get_client; \
c=get_client(); \
c.post('/task/<task_id>/comment', json={'comment_text': '<evidence: facts, links, results>'})"
```

## 4. Block

```bash
python update_task.py <task_id> --status blocked
python -c "from client import get_client; \
c=get_client(); \
c.post('/task/<task_id>/tag/waiting-on-andres'); \
c.post('/task/<task_id>/comment', json={'comment_text': 'BLOCKER: <precise reason + what unblocks>'})"
```

## 5. Review

```bash
python update_task.py <task_id> --status review
python -c "from client import get_client; \
c=get_client(); \
c.post('/task/<task_id>/comment', json={'comment_text': 'Ready for review: <what to check, who reviews>'})"
```

## 6. Complete

```bash
python update_task.py <task_id> --status complete
python -c "from client import get_client; \
c=get_client(); \
c.post('/task/<task_id>/comment', json={'comment_text': 'DONE: <evidence>'})"
```

## Agent identity

Every agent runs as `<Harness>@<Device>` — title-cased (capitalize the first
letter of each half), stable across sessions, e.g. `Pi@Macbook`, `Pi@Phone`,
`Opencode@Desktop`:
- `<Harness>` — the runtime the agent runs inside, from the harness registry
  (e.g. `Pi`, `Hermes`, `Minimax-code`, `Opencode`).
- `<Device>` — the physical machine, from the device registry (e.g. `Macbook`,
  `Desktop`, `Phone`).

Stable identity keeps ownership trackable; do not change it mid-effort. The
matching identity tags stay lowercase in the space (`pi`, `macbook`); the
title-cased form is used in the Owner field, the `Owner:` description line,
and comments.

## Pitfalls

| Pitfall | Workaround |
|---|---|
| Space-level status query shows only `to do`/`complete` | Statuses are list-level (`override_statuses=true`); read them from `GET /list/{id}` |
| General list hides under a "hidden" folder | It is space-level; query `/space/{id}/list` — the folder is not meaningful |
| Status strings are case-sensitive | Use exact lowercase: `in progress`, `review`, `blocked`, `complete` |
| Closed tasks invisible without a flag | Always `include_closed=true` when querying |
| `update-task --tags` silently drops new tags | Tags apply only at creation; add to existing tasks via `POST /task/{id}/tag/<name>` |
| Custom fields don't show in `fields` | Read them under `custom_fields` on the task object |
| Stale reads | use-clickup caches GETs (tasks 1 min); any write clears the cache — re-read after writes |
| Cold-agent resume | Description must carry objective + context + verified facts + next steps |
