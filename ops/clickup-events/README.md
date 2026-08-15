# clickup-events — the Agents space poller

Wake-the-hands daemon for the shared ClickUp **Agents** space (team 90132304521).
Audit-verified behavior (2026-08-15): team query + `space_ids[]` + `date_updated_gt`
work; 429 = shared rate limit (sleep Retry-After); cursor advances ONLY on success.

## What it does (per 60s tick)

- Fetches tasks changed since the cursor: `GET /team/90132304521/task?space_ids[]=<space>&date_updated_gt=<cursor>&include_closed=true`
- Diffs (status, tags) per task against `~/.local/state/clickup-events/state.json`
- Fires only on transitions:
  - → `to do` (Andrés's GO) → notify "Released" (+ spawn when armed)
  - → `blocked` → notify "stuck — read the blocker comment"
  - → `review` → notify "ready for your accept"

## Modes

- Default: **NOTIFY-ONLY** (termux-notification).
- `--spawn`: also spawn a herdr pi pane on `to do` (explicitly armed; the exact
  herdr agent-start command is a TODO in the script — wire it before arming).
- `--once`: single tick (test).

## Deploy (per device — phone AND tablet for the failover pair)

1. Copy files:
   ```bash
   cp clickup-poller.py ~/bin/
   chmod +x ~/bin/clickup-poller.py
   SVDIR=/data/data/com.termux/files/usr/var/service
   mkdir -p $SVDIR/clickup-events/log
   cp service/run $SVDIR/clickup-events/run && chmod +x $SVDIR/clickup-events/run
   cp service/log/run $SVDIR/clickup-events/log/run && chmod +x $SVDIR/clickup-events/log/run
   ```
2. Test one tick: `python3 ~/bin/clickup-poller.py --once`
3. Enable + verify:
   ```bash
   export SVDIR=/data/data/com.termux/files/usr/var/service
   export LOGDIR=/data/data/com.termux/files/usr/var/log
   service-daemon start      # ensure runsvdir is supervising
   sv-enable clickup-events
   sv status clickup-events  # expect: run
   ```
4. Prereqs per device: `CLICKUP_API_KEY` in `~/storage/shared/Projects/.env` (or env),
   `termux-api` installed (notifications), herdr running (for spawns, when armed).

## Failover pair

Run on both phone and tablet. Whichever is awake fires; the claim comment arbitrates
(spawned sessions re-read and release on conflict). Combined rate cost ≈ 2% of the shared
100 req/min budget.

## Notes

- Battery: wake-lock is OFF by default (uncomment one line in `service/run` to arm —
  ticks may delay while the screen is off otherwise).
- The state file makes restarts idempotent; first boot sets cursor=now (no replay).
- Source of truth: this repo. Devices deploy from it (`skills update` for skills;
  `ops/clickup-events/` for the poller).
