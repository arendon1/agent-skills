# agents-pm — Workflows (v2)

Exact commands for the agents-pm lifecycle. All commands run through the `use-clickup`
skill (its `scripts/` directory). Adjust the command prefix to the local installation.
`<hand>` = the agent's device-harness identity used in claim comments, e.g. `phone-pi`,
`tablet-pi`, `macbook-pi` (plain lowercase; identity lives ONLY in claim comments).

## 0. Read the space (session start / after compaction)

Open + closed tasks in General, grouped by status, with work-type tags:

```python
# run from the use-clickup skill's scripts/ directory
from client import get_client
c = get_client()
tasks = c.get("/list/1000270000008318/task",
              params={"include_closed": "true"}).json()["tasks"]
for t in sorted(tasks, key=lambda x: x.get("date_updated", ""), reverse=True):
    st = t.get("status", {}).get("status")
    tags = [tag["name"] for tag in t.get("tags", [])]
    print(st, "|", t["name"][:55], "|", ",".join(tags))
```

Per-status views — the "needs Andrés" queue (review + blocked):

```python
r = c.get("/list/1000270000008318/task",
          params={"include_closed": "true", "statuses[]": "review"})
for t in r.json()["tasks"]:
    print(t.get("status", {}).get("status"), "|", t["name"][:60])
```

Or the script (open tasks only):

```bash
python search_task.py --list_id 1000270000008318
```

Group mentally by status. Surface `review` (accept queue) and `blocked` (read the blocker
comment) first, then `in progress` (claim comments tell who's on what).

## 1. Scope before work

Search before starting — no work without a ticket. **Global text search does not exist**;
use the team query + client-side keyword match:

```python
from client import get_client
c = get_client()
r = c.get("/team/90132304521/task", params={"include_closed": "true"})
hits = [t for t in r.json()["tasks"] if "<keyword>" in t["name"].lower()]
```

Create a missing task with a self-contained description AND work-type tags:

```bash
python create_task.py 1000270000008318 "Short actionable title" \
  --description "## Objective\n<what and why>\n\n## Next steps\n1. ..." \
  --tags research,analysis
```

(New task lands in `backlog` by default — statuses are lowercase exact.)

## 2. Claim

```bash
python update_task.py <task_id> --status "in progress"
python -c "
from client import get_client
c = get_client()
c.post('/task/<task_id>/comment', json={'comment_text': 'Claimed by phone-pi — <what I will deliver>'})
"
```

Then RE-READ the task; if another hand's claim comment appears, release
(`--status "to do"`) and back off. Multi-step ticket? Add subtasks:

```bash
python -c "
from client import get_client
c = get_client()
c.post('/list/1000270000008318/task', json={'name': '<step>', 'parent': '<task_id>', 'status': 'backlog'})
"
```

## 3. Update (progress)

```bash
python update_task.py <task_id> --description "<refreshed, self-contained, Evidence Log appended>"
python -c "from client import get_client; \
c=get_client(); \
c.post('/task/<task_id>/comment', json={'comment_text': '<evidence: facts, links, results>'})"
```

## 4. Block

```bash
python update_task.py <task_id> --status blocked
python -c "from client import get_client; \
c=get_client(); \
c.post('/task/<task_id>/comment', json={'comment_text': 'BLOCKER: <precise reason + who/what unblocks>'})"
```

No tag needed — `blocked` status IS the escalation surface.

## 5. Review

```bash
python update_task.py <task_id> --status review
# fill ## Proof of work in the description
python -c "from client import get_client; \
c=get_client(); \
c.post('/task/<task_id>/comment', json={'comment_text': 'Ready for accept: <what to check>'})"
```

## 6. Complete

Only Andrés moves `review` → `complete`. After accept, the task closes (query with
`include_closed=true`; `statuses[]=complete` returns them even without the flag).

## Hand identity

Identity is carried ONLY by the claim comment (`Claimed by <hand> — <plan>`). Use plain
lowercase `<device>-<harness>` forms: `phone-pi`, `tablet-pi`, `macbook-pi`,
`desktop-pi`, `macbook-opencode`, etc. There is no Owner field, no identity tags.

## Pitfalls

| Pitfall | Workaround |
|---|---|
| Status names are stored lowercase | Match exactly: `in progress`, `review`, `complete` (updates are case-insensitive, readbacks are lowercase) |
| Closed tasks invisible without a flag | `include_closed=true` (or `statuses[]=complete` explicitly) |
| `update-task --tags` silently drops tags | Tags apply at creation only; add via `POST /task/{id}/tag/<name>` (auto-creates) |
| Global search 404s | Team query `GET /team/{id}/task` + client-side keyword match |
| Custom fields 403/400 | None exist — never try to use them |
| Stale reads | use-clickup caches GETs (tasks 1 min); any write clears the cache — re-read after writes |
| Rate limit (429) | Shared ~100/min per key across devices; back off Retry-After 60; keep polling light |
| Markdown headings vanish in GET | Send descriptions as plain text (`markdown_description=False`) |
| Cold-agent resume | Description must carry Objective + Goal + Evidence Log + Next steps |
| Docs | Banned — never create; artifacts are local files linked in the description |
