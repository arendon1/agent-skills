# agents-pm — Workflows

Exact commands for the agents-pm lifecycle. All commands run through the
`use-clickup` skill (its `scripts/` directory). Adjust the command prefix to
the local installation of that skill.

## 0. Read the space (session start / after compaction)

Open + closed tasks in General, grouped by status:

```python
# run from the use-clickup skill's scripts/ directory
from client import get_client
c = get_client()
tasks = c.get("/list/1000270000007301/task",
              params={"include_closed": "true"}).json()["tasks"]
for t in sorted(tasks, key=lambda x: x.get("date_updated", ""), reverse=True):
    st = t.get("status", {}).get("status")
    owner = [l for l in (t.get("description") or "").splitlines()
             if l.startswith("Owner:")]
    tags = [tag["name"] for tag in t.get("tags", [])]
    print(st, "|", t["name"][:60], "|", (owner[0] if owner else "-"),
          "|", ",".join(tags))
```

Or the script (open tasks only):

```bash
python search_task.py --list_id 1000270000007301
```

Group mentally by status. Surface `waiting-on-andres` tags to the operator
first, then `blocked`, then `in progress` ownership.

## 1. Scope before work

Search before starting — no work without a task:

```bash
python search_task.py --name "<keyword>"
# workspace-wide, including closed:
python -c "from search_task import search_workspace_tasks; \
import json; print(json.dumps(search_workspace_tasks(team_id='90132304521', \
include_closed=True), indent=1)[:4000])"
```

Create a missing task with a self-contained description:

```bash
python create_task.py 1000270000007301 "Short actionable title" \
  --description "## Objective\n<what and why>\n\n## Context\n<pointers>\n\n## Next steps\n1. ..." \
  --tags skill
```

## 2. Claim

```bash
python update_task.py <task_id> --status "in progress"
# Owner line + start comment via client:
python -c "from client import get_client; \
c=get_client(); \
c.post('/task/<task_id>/comment', json={'comment_text': 'Started by <agent-identity>: <what + ETA>'})"
```

The Owner line goes into the description (first line): `Owner: <agent-identity>`.

## 3. Update (progress)

```bash
python update_task.py <task_id> --description "<refreshed, still self-contained>"
python -c "from client import get_client; \
c=get_client(); \
c.post('/task/<task_id>/comment', json={'comment_text': '<evidence: facts, links, results>'})"
```

## 4. Block

```bash
python update_task.py <task_id> --status blocked --tags waiting-on-andres
python -c "from client import get_client; \
c=get_client(); \
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

Every agent must name itself stably across sessions. `<agent-identity>` is
that name, used in Owner lines and comments (e.g. a personal alias or the
machine hostname). Stable names keep ownership trackable; do not change
identity mid-effort.

## Pitfalls

| Pitfall | Workaround |
|---|---|
| Space-level status query shows only `to do`/`complete` | Statuses are list-level (`override_statuses=true`); read them from `GET /list/{id}` |
| General list hides under a "hidden" folder | It is space-level; query `/space/{id}/list` — the folder is not meaningful |
| Status strings are case-sensitive | Use exact lowercase: `in progress`, `review`, `blocked`, `complete` |
| Closed tasks invisible without a flag | Always `include_closed=true` when querying |
| Stale reads | use-clickup caches GETs (tasks 1 min); any write clears the cache — re-read after writes |
| Cold-agent resume | Description must carry objective + context + verified facts + next steps |
