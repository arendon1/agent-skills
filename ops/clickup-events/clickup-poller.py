#!/usr/bin/env python3
"""clickup-poller — wake-the-hands daemon for the Agents space.
Audit-verified (2026-08-15): team query + space_ids[] + date_updated_gt work; 429 = shared
rate limit (sleep Retry-After); cursor advances ONLY on success; state in
~/.local/state/clickup-events/state.json.

Modes:
  default   NOTIFY-ONLY — termux-notification on transitions (to do / blocked / review)
  --spawn   ALSO spawn a herdr pi pane when a task enters `to do` (arm explicitly!)
  --once    single tick (test mode)
"""
import json, os, sys, time, subprocess, urllib.request, urllib.error
from datetime import datetime

TEAM = "90132304521"
SPACE = "1000270000004203"          # Agents
V2 = "https://api.clickup.com/api/v2"
STATE = os.path.expanduser("~/.local/state/clickup-events/state.json")
LOG = os.path.expanduser("~/.local/state/clickup-events/events.log")
INTERVAL = 60                        # seconds between ticks
SPAWN_ENABLED = "--spawn" in sys.argv
ONCE = "--once" in sys.argv
NOTIFY_TITLE = "Agents"

def log(msg):
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def notify(task_id, title, content):
    try:
        subprocess.run(["termux-notification", "--title", title,
                        "--content", content[:200], "--id", str(task_id)],
                       timeout=10, check=False)
    except Exception as e:
        log(f"notify failed: {e}")

def spawn(task_id, name):
    if not SPAWN_ENABLED:
        return
    # TODO(arm): wire the exact herdr agent-start command for a pi pane seeded with the
    # ticket. Keep the claim-lock re-read inside the spawned session.
    log(f"SPAWN requested for {task_id} ({name}) — spawn not yet wired")

def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {"cursor": None, "tasks": {}}

def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, STATE)

def fetch_changed(cursor):
    url = f"{V2}/team/{TEAM}/task?space_ids[]={SPACE}&include_closed=true"
    if cursor:
        url += f"&date_updated_gt={cursor}"
    r = urllib.request.Request(url, headers={"Authorization": os.environ["CLICKUP_API_KEY"]})
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode())["tasks"]

def tick(st):
    now_ms = int(time.time() * 1000)
    try:
        tasks = fetch_changed(st["cursor"])
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry = int(e.headers.get("Retry-After", "60"))
            log(f"429 rate limit — sleeping {retry}s")
            time.sleep(min(retry, 60))
            return False
        log(f"HTTP {e.code} — skipping tick")
        return False
    except Exception as e:
        log(f"network error: {e} — skipping tick")
        return False

    seen = {}
    for t in tasks:
        tid = t["id"]
        st_now = t.get("status", {}).get("status")
        tags = sorted(tag["name"] for tag in t.get("tags", []))
        seen[tid] = {"status": st_now, "tags": tags, "name": t["name"]}
        prev = st["tasks"].get(tid)
        if prev and prev["status"] != st_now:
            if st_now == "to do":
                notify(tid, NOTIFY_TITLE, f"Released: {t['name']}")
                spawn(tid, t["name"])
            elif st_now == "blocked":
                notify(tid, NOTIFY_TITLE, f"BLOCKED: {t['name']} — read the blocker comment")
            elif st_now == "review":
                notify(tid, NOTIFY_TITLE, f"Ready for your accept: {t['name']}")
        # tag changes are informative only for now
    st["tasks"] = seen
    st["cursor"] = now_ms          # advance ONLY after a successful fetch
    save_state(st)
    return True

def main():
    st = load_state()
    if st["cursor"] is None:
        # first boot: no history replay
        st["cursor"] = int(time.time() * 1000)
        save_state(st)
        log("first boot — cursor=now, no replay")
    while True:
        tick(st)
        if ONCE:
            return
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
