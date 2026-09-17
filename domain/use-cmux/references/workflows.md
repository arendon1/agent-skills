# Workflows — full worked examples with pitfalls

The `SKILL.md` sketches workflows A–E. This file is the long version: exact
command sequences, polling loops, error recovery, and the failure modes that
bite in practice.

## Workflow A — run a dev server in a dedicated pane

### Full sequence

```bash
# 0. Gate on cmux.
command -v cmux >/dev/null 2>&1 || { echo "no cmux"; exit 1; }

# 1. Create an isolated workspace, cd into the project, start the server.
#    --command sends text+Enter to the first terminal after creation.
#    Use the canonical noun verb with --json: it returns
#    {workspace_ref, surface_ref, window_ref, group_ref}.
WS=$(cmux --json workspace create --name "dev-server" --cwd ~/projects/myapp \
       --command "npm run dev" --focus false \
       | python3 -c 'import sys,json;print(json.load(sys.stdin)["workspace_ref"])')
#  Gotcha: the legacy `cmux --json new-workspace` prints plain text
#  ("OK workspace:14") and ignores --json — `json.load` would throw. Either use
#  `workspace create` (above) or regex the ref:
#    WS=$(cmux new-workspace --name dev-server --cwd ~/projects/myapp \
#           --command "npm run dev" --focus false | grep -oE 'workspace:[0-9]+')

# 2. Poll the tail for the ready line. Don't block on a single long wait.
for i in $(seq 1 30); do
  OUT=$(cmux read-screen --workspace "$WS" --scrollback --lines 30)
  echo "$OUT" | grep -q "Local:.*localhost:" && break
  echo "$OUT" | grep -qi "error" && { echo "server failed to boot"; break; }
  sleep 2
done

# 3. Extract the port.
PORT=$(echo "$OUT" | grep -oE "localhost:[0-9]+" | head -1 | cut -d: -f2)
echo "server up on :$PORT"

# 4. Open it in a browser surface (Workflow B).
SURF=$(cmux --json browser open "http://localhost:$PORT" \
        | python3 -c 'import sys,json;print(json.load(sys.stdin)["surface_ref"])')

# 5. Watch logs on demand.
cmux read-screen --workspace "$WS" --scrollback --lines 200

# 6. Stop and clean up.
cmux send-key --workspace "$WS" ctrl+c
cmux workspace close "$WS"
```

### Pitfalls

1. **`new-workspace --command` sends to the FIRST terminal, not a named one.**
   If you passed `--layout` with multiple surfaces each defining a `command`,
   `--command` is ignored (layout surfaces define their own). Use `cmux send`
   to target a specific surface in a layout workspace.

2. **`read-screen --scrollback --lines N` returns the last N lines of the
   scrollback, not the last N lines of the visible viewport.** For a quick
   "what's on screen now" use bare `read-screen` (no flags). For "did the
   server print its port" use `--scrollback --lines 30`.

3. **The server prints its port to stdout, which cmux captures.** But if the
   server forks to the background or redirects to a file, `read-screen` won't
   see it. Prefer servers that log to the terminal (`npm run dev`,
   `mvn spring-boot:run`); for ones that daemonize, tail their log file in the
   same surface: `cmux send --workspace "$WS" "tail -f server.log\n"`.

5. **`--json` is per-subcommand, not global — check before you parse.** In cmux
   0.64.22 `workspace list --json`, `workspace create --json`,
   `workspace-group list --json`, `workspace-group create --json`, `identify
   --json`, and the `browser` verbs return JSON; the legacy `new-workspace`,
   `list-workspaces`, and every other `workspace-group` verb print text (`OK
   workspace:N`). A parse that assumes JSON on a text verb throws before the
   command's work is undone — the workspace is still created. Regex the handle
   or re-run `list --json` to resync.

6. **`workspace list --json` includes `listening_ports`.** Before scraping
   `read-screen` for a port, try:

   ```bash
   cmux --json workspace list \
     | python3 -c 'import json,sys;[print(w["ref"], w["listening_ports"]) for w in json.load(sys.stdin)["workspaces"]]'
   ```

   It reports what cmux has observed the workspace listening on — a fast,
   grep-free way to answer "did the server come up, and on which port".
   It does **not** say the process is healthy, so still `read-screen` the ready
   line before declaring victory. Note `workspace list --json` also exposes
   `group_ref`, but in 0.64.22 it is `null` even for grouped workspaces — read
   membership from `workspace-group list --json` instead.

5. **Don't lose the handle.** If you didn't capture `WS` from `new-workspace`,
   recover it: `cmux list-workspaces` (match by name) or `cmux tree --all`.

### Servers that need env vars

```bash
cmux new-workspace --name "api" --cwd ~/projects/api \
  --env DATABASE_URL="postgres://localhost/dev" \
  --env PORT=8080 \
  --command "npm start"
# or from a file:
cmux new-workspace --name "api" --cwd ~/projects/api \
  --env-file ~/projects/api/.env --command "npm start"
```

Reserved `CMUX_*` variables cannot be overridden. Inspect a workspace's env:
`cmux workspace env <workspace> --mask` (redacts values so secrets aren't
echoed in full).

## Workflow B — preview a localhost webapp

### Full sequence

```bash
# 1. Open the URL in a browser surface in the caller's workspace.
SURF=$(cmux --json browser open http://localhost:5173 \
        | python3 -c 'import sys,json;print(json.load(sys.stdin)["surface_ref"])')

# 2. Confirm navigation (empty/about:blank => navigate first).
cmux browser "$SURF" get url

# 3. Wait for readiness. Pick the most specific signal:
cmux browser "$SURF" wait --load-state complete --timeout-ms 15000
cmux browser "$SURF" wait --selector "#root > *:first-child" --timeout-ms 10000
cmux browser "$SURF" wait --text "Dashboard" --timeout-ms 10000
cmux browser "$SURF" wait --url-contains "/dashboard" --timeout-ms 10000

# 4. Snapshot for fresh element refs, then act.
cmux browser "$SURF" snapshot --interactive
cmux browser "$SURF" fill "#email" "user@example.com"
cmux --json browser "$SURF" click "#submit" --snapshot-after

# 5. Capture evidence.
cmux browser "$SURF" screenshot --out /tmp/preview.png
cmux browser "$SURF" get text body
```

### Pitfalls

1. **Refs go stale after navigation, modal open/close, or major DOM changes.**
   Re-snapshot before acting again. `--snapshot-after` on a mutating action
   returns the fresh snapshot in one call — prefer it.

2. **`snapshot --interactive` can `js_error` on complex pages.** Recover:
   check `get url` (did it navigate?), then fall back to raw text/HTML:
   `cmux browser "$SURF" get text body` / `get html body`. If still failing,
   navigate to a simpler intermediate page and retry.

3. **Browser surfaces target the caller's workspace** (`CMUX_WORKSPACE_ID`),
   even when another workspace is focused. To open in a different workspace:
   `cmux browser open <url> --workspace workspace:2 --window window:1`.

4. **WKWebView is not Chrome.** Offline emulation, network route interception,
   trace/screencast recording, and raw input injection return `not_supported`.
   Use `click`, `fill`, `press`, `scroll`, `wait`, `snapshot` instead. Full
   gap list in the official `cmux-browser` skill (`cmux docs browser`).

5. **Opening a browser pane vs a browser surface.** `cmux new-pane --type
   browser --url <url>` creates a new split pane that is a browser;
   `cmux browser open <url>` creates a browser surface (tab) in the current
   workspace's pane. For a localhost preview you usually want `browser open`
   (stays in your workspace). For a dedicated always-visible preview, use
   `new-pane --type browser --direction right`.

6. **Viewport emulation.** `cmux browser "$SURF" viewport 1280 720` sets an
   exact CSS-pixel viewport without resizing the pane; `viewport reset`
   restores native sizing. Close/detach the browser inspector first — its
   split layout conflicts with viewport emulation.

7. **Remote dev servers over SSH workspaces.** Browser panes route through the
   remote network, so `http://localhost:PORT` just works against a dev server
   running on the remote host — no port forwarding needed. This is the
   intended way to preview a remote dev server from inside an SSH workspace.

## Workflow C — parallel work in its own surface

### Full sequence

```bash
# 1. Split the current pane to the right (keeps focus by default? no — 
#    --focus defaults to false, so you stay put).
cmux new-split right
#  parse the new surface ref from output, or:
cmux list-pane-surfaces   # find the new surface in the new pane

# 2. Send a command to the new surface.
cmux send --surface surface:8 "npm test 2>&1 | tee /tmp/test.log\n"

# 3. Poll for completion without leaving your pane.
for i in $(seq 1 60); do
  OUT=$(cmux read-screen --surface surface:8 --scrollback --lines 5)
  echo "$OUT" | grep -qiE "(passed|failed|[0-9]+ tests)" && break
  sleep 3
done

# 4. Read the full result.
cmux read-screen --surface surface:8 --scrollback --lines 200
```

### Pitfalls

1. **`new-split` splits the pane, creating a new pane with one surface.** The
   new surface ref is what you `send` to. If you `send` to the old surface ref,
   you type into your own pane. Always capture the new ref or find it via
   `list-pane-surfaces`.

2. **`send` with `\n` sends Enter.** `send "ls -la"` (no `\n`) types the text
   without executing — useful to pre-fill a command for the human to review,
   not to run it. To run, append `\n` or follow with `send-key enter`.

3. **`read-screen` on a surface mid-command returns partial output.** Detect
   completion by looking for a shell prompt or a known result line, not by
   "output stopped changing" (a long pause may be legitimate work).

4. **For fully isolated parallel work, use `new-workspace` not `new-split`.**
   A split shares the workspace's cwd and todos; a workspace is isolated. Use
   splits for "watch this alongside"; use workspaces for "a separate project
   context".

## Workflow D — launch a peer agent in its own surface

### Option 1 — first-class agent-session surface

```bash
cmux new-surface --type agent-session --provider codex \
  --working-directory ~/projects/myapp --focus true
```

Providers: `codex`, `claude`, `opencode`. The surface wires session-restore
and the Feed permission bridge automatically. Renderer defaults to `react`
(`solid` is an alternative).

### Option 2 — bare command in a new workspace

```bash
cmux new-workspace --name "reviewer" --cwd ~/projects/myapp \
  --command "<agent-launch-command>" --focus false
```

### Option 3 — first-class launcher command

cmux ships launcher commands that open an agent with pane integration. See
`agent-launchers.md` for the full list (e.g. `cmux omo`, `cmux claude-teams`,
`cmux codex-teams`). Prefer these over a bare `--command` when they match the
harness — they install the hooks that make session-restore and Feed work.

### Pitfalls

1. **One surface per agent.** Stacking multiple agent sessions in one pane's
   tabs means `read-screen` can only see the visible one. Give each agent its
   own surface (or workspace) and poll them in turn.

2. **Agent Hibernation may reclaim idle background agent terminals.** It is
   opt-in (`cmux agent-hibernation on`) and off by default, but if enabled, a
   background idle agent surface may be SIGTERM'd after the idle window and
   resumed when you return to its tab. Do not assume a background agent
   process is still alive — `read-screen` to check; if hibernated, the
   placeholder shows a Resume button. Make your launch commands re-runnable
   (the hooks save the session ID and resume it).

3. **The Feed bridges permission requests.** When a peer agent wants to run a
   tool, edit a file, or run a shell command, the request appears in the Feed
   (right sidebar, `Ctrl-4`) for a human to approve — unless the agent's
   permissions are pre-configured. An agent driving cmux should not auto-approve
   on behalf of a peer; surface the request to the human via `cmux notify` if
   urgent, and let the human use Feed.

## Workflow E — a group per project (keep the sidebar sane)

Use when a session spawns more than ~2 workspaces for one effort, or when you
find yourself in someone else's window with an unrelated group already there.
The goal: the human's sidebar gains one collapsible row, not N tabs, and you can
re-find your own workspaces later.

### Full sequence

```bash
# 0. Inventory first. Groups are invisible in `cmux tree`, so this is the only
#    way to know what already exists and what is free to reuse.
cmux --json workspace-group list \
  | python3 -c 'import json,sys;[print(g["ref"], repr(g["name"]), g["member_workspace_refs"]) for g in json.load(sys.stdin)["groups"]]'

# 1. Create or reuse. Reuse the existing group if the project already has one —
#    do not stack a second group on top of a project.
GRP=$(cmux --json workspace-group create --name "feature-x" --cwd ~/projects/myapp \
        | python3 -c 'import sys,json;print(json.load(sys.stdin)["group"]["ref"])')

# 2. Spawn each new workspace directly into it (no separate `add` needed).
WS=$(cmux --json workspace create --name "dev-server" --cwd ~/projects/myapp \
       --command "npm run dev" --focus false \
       | python3 -c 'import sys,json;print(json.load(sys.stdin)["workspace_ref"])')
cmux workspace-group add --group "$GRP" --workspace "$WS"
#    ^ two steps because `workspace create --json` reports group_ref only when
#    it was created with --group. The single-call form is:
#      cmux new-workspace --group "$GRP" --group-placement top --name dev-server \
#        --cwd ~/projects/myapp --command "npm run dev" --focus false
#    (prints "OK workspace:N" — regex the ref, --json is ignored by the legacy verb)

# 3. Adopt workspaces you created before deciding to group them.
cmux workspace-group add --group "$GRP" --workspace workspace:9

# 4. Do the work; poll each member with read-screen as usual.
cmux read-screen --workspace "$WS" --scrollback --lines 40

# 5. Leave the sidebar tidy. Stop processes FIRST, then ungroup (safe: members
#    survive as ordinary workspaces), then close only the workspaces you own.
cmux send-key --workspace "$WS" ctrl+c
cmux workspace-group remove --workspace "$WS"   # out of the group…
cmux workspace close workspace:9                 # …then gone entirely
cmux workspace-group list --json                 # verify
```

### When the human's own groups exist

Never delete, rename, recolor, unpin, or re-anchor a group you did not create.
`workspace-group list --json` gives you `name`/`member_count`, but **no
created-by marker** — so the tell is provenance: a group whose name you did not
choose, or whose members include workspaces with cwds like a human's project,
is not yours. Treat it read-only and ask if you think it should change.

### Pitfalls

1. **`add` moves silently.** `workspace-group add` sets `Workspace.groupId`,
   which is a single field — a workspace already in another group is removed
   from it with no warning. Before `add`, check
   `workspace-group list --json` for the workspace ref you are about to move.

2. **`remove` takes no `--group`.** It is a property of the workspace, not of
   the group: `cmux workspace-group remove --workspace W`. Passing `--group` is
   not the documented form; passing a group as the positional arg expects a
   workspace handle.

3. **The anchor is a real workspace and can be closed.** The header row *is*
   the anchor workspace; there is no separate row. Closing that workspace may
   either promote the next member (installed CLI help, 0.64.22) or dissolve the
   group (public docs page) — the two texts disagree. Never close an anchor to
   "tidy up": reset the group with `remove`/`ungroup`, which have defined
   semantics. If you must, re-read `workspace-group list --json` afterwards to
   see what the app actually did.

4. **`delete --close-workspaces` is a kill switch.** It closes the anchor and
   every member — Ctrl-C'ing nothing, just closing terminals, so a dev server
   dies and a peer agent's session ends. This is the one group verb that
   destroys work. Reserve it for groups you created whose processes you already
   stopped.

5. **Groups do not nest and are not visible in the tree.** No group inside a
   group, and `cmux tree --all` renders a grouped workspace as a flat top-level
   row. Any script that infers structure from the tree will be wrong about
   grouping — always cross-check `workspace-group list --json`.

6. **Pin tiers reorder the sidebar.** Pinned top-level rows (workspaces *and*
   groups) sort above unpinned rows; within each tier the human's drag order
   holds. Unpinning or pinning a group therefore moves the whole section — do
   not do it as a side effect of an unrelated task.

## Cross-workflow: live docs while you work

```bash
# Open the active plan in a markdown viewer that live-reloads on file change.
cmux markdown open docs/plans/2026-07-28-feature-x/PLAN.md --direction right

# Update the plan on disk (the agent edits the file); the viewer refreshes.
# Mirror the plan's tasks into the workspace todo for at-a-glance status:
cmux todo set '[
  {"text":"scaffold API","state":"completed"},
  {"text":"wire auth","state":"in-progress"},
  {"text":"write tests","state":"pending"}
]'
cmux todo list

# Surface a status pill + progress in the sidebar:
cmux set-status --text "building" --color blue
cmux set-progress --value 0.6
cmux log "step 3/5: integration tests running"

# When done:
cmux notify --title "Build complete" --body "32/32 tests passed"
cmux clear-status
cmux clear-progress
```
