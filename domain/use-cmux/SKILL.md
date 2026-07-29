---
name: use-cmux
description: |
  Drive the cmux terminal multiplexer from an agent session: give each
  long-lived process (dev server, build watcher, test runner) its own pane,
  open localhost webapps in browser surfaces, run parallel work in dedicated
  surfaces, launch peer agent sessions with isolated cwd/output/lifecycle,
  send commands, read output, and signal completion via notifications.
  Use when the agent must run a long-lived process in a dedicated pane, preview
  a localhost URL in a browser panel, give a parallel task or peer agent its
  own surface, monitor or control a pane's output, manage terminal topology
  across windows/workspaces/panes/surfaces, or coordinate multiple agent
  sessions that each need their own terminal.
invocation: auto
layer: domain
provides: [terminal-topology]
language: en-US
metadata:
  version: "1.0.0"
---

# use-cmux

Domain capability for terminal topology control via the `cmux` CLI. cmux is a
macOS terminal multiplexer controlled through a Unix socket. An agent running
inside a cmux surface can create, target, and drive other surfaces
programmatically — the same primitives a human uses interactively, but
scriptable. This skill teaches the agnostic topology patterns; the harness
adapter maps "launch a peer agent" to the concrete binary.

**Canonical source:** `cmux docs` prints live URLs + raw resources for every
topic. `cmux docs api`, `cmux docs agents`, `cmux docs browser` are the entry
points. The cmux project publishes its own skills (`cmux`, `cmux-browser`,
`cmux-workspace`, `cmux-settings`) — read them with `cmux docs <topic>` when
this skill's references are insufficient.

## The model

```
window        top-level macOS window
└── workspace   tab-like group within a window (has a cwd, env, todos, status)
    └── pane      split container in a workspace
        └── surface   a tab within a pane: terminal | browser | agent-session
```

- **Window → workspace → pane → surface.** A surface is the addressable unit:
  it holds a terminal, a browser webview, or an agent session. Commands that
  "send text" or "read output" target a surface.
- **Handles.** Output defaults to short refs: `window:1`, `workspace:2`,
  `pane:3`, `surface:4`. UUIDs are accepted as input; request them with
  `--id-format uuids|both` only when you must log a stable ID.
- **Caller context.** Every cmux terminal exports `CMUX_WORKSPACE_ID`,
  `CMUX_SURFACE_ID`, `CMUX_WINDOW_ID`(?), `CMUX_TAB_ID`. Most commands default
  to the caller's workspace/surface, so "the current pane" needs no flag.

Discover where you are and what exists:

```bash
cmux identify --json          # caller context: pane/surface/workspace/window refs
cmux tree --all               # full window>workspace>pane>surface tree
cmux list-workspaces          # workspaces in the caller's window
cmux list-panes               # panes in the caller's workspace
cmux list-pane-surfaces       # surfaces in the caller's (or --pane's) pane
cmux capabilities             # server capabilities as JSON
```

`cmux identify --json` is the first command to run in any session — it tells
you the surface you are running in, so you can target *other* surfaces
explicitly instead of clobbering your own.

## Prerequisite: is cmux present?

Always gate on cmux availability. An agent may run outside cmux (plain
terminal, CI, SSH). Degrade gracefully:

```bash
if command -v cmux >/dev/null 2>&1; then
  : # cmux present — use the topology commands below
else
  : # no cmux — run the process inline / in the background instead
fi
```

If `CMUX_SURFACE_ID` is unset, you are not inside a cmux terminal; topology
commands still work (they talk to the socket) but "the current pane" is
undefined — pass explicit `--workspace`/`--surface` handles.

## Core principle — one surface per long-lived process

The single rule that makes cmux worth driving from an agent: **give each
long-lived or parallel process its own surface.** A dev server, a build
watcher, a test runner, a peer agent, a log tail — each gets a dedicated
surface with its own cwd, output buffer, and lifecycle. You start it once,
leave it running, and poll its output with `read-screen` instead of blocking
the session on a foreground command with a giant timeout.

This is the cmux-native alternative to a harness's built-in subagent dispatch
when the work is a *process* (something that stays alive) rather than a *task*
(something that returns a result). For result-returning parallel tasks, prefer
the harness's native subagent tool; for long-lived processes, use a surface.

## Workflow A — run a dev server in a dedicated pane

The canonical case: start `npm run dev` / `mvn spring-boot:run` /
`python -m http.server` and keep it alive while you work, capturing its output
on demand.

```bash
# 1. Create an isolated workspace for the server, cd into the project, and
#    send the start command. --command sends text+Enter after creation.
cmux new-workspace --name "dev-server" --cwd ~/projects/myapp \
  --command "npm run dev" --focus false
# -> prints workspace:N

# 2. Let it boot, then read the tail to confirm it's up and grab the port.
cmux read-screen --workspace workspace:N --scrollback --lines 40

# 3. Once you see "Local: http://localhost:5173", open it (Workflow B).

# 4. Watch logs on demand without switching focus:
cmux read-screen --workspace workspace:N --scrollback --lines 200

# 5. Stop the server when done (send Ctrl-C to its surface):
cmux send-key --workspace workspace:N ctrl+c

# 6. Close the workspace:
cmux workspace close workspace:N
```

Why a *workspace* and not a *split*: a dev server is long-lived and noisy; a
separate workspace keeps it out of your editing pane's scrollback and lets it
survive independently. Use `new-split` (Workflow C) only for short-lived
parallel work you want to watch alongside.

**Capture the handle.** `new-workspace` prints the ref. Parse it (or use
`--json`) and reuse it — do not assume "workspace:2" stays stable across
sessions. `cmux identify --json` and `cmux tree --all` re-derive handles if
you lost them.

**Don't block on boot.** Dev servers take 2–30s to print their port. Poll
`read-screen --lines 20` a few times with a short sleep between, or `grep` the
output for the port pattern, rather than a single long foreground wait.

## Workflow B — preview a localhost webapp in a browser surface

cmux has a built-in WKWebView browser surface — open a localhost URL in a pane
and drive it like a headless browser (snapshot, click, fill, wait, screenshot).

```bash
# Open a URL in a new browser surface in the caller's workspace.
# Returns a surface ref, e.g. surface:7
cmux --json browser open http://localhost:5173

# Verify it navigated (empty/about:blank means navigate first):
cmux browser surface:7 get url

# Wait for the app to be ready:
cmux browser surface:7 wait --load-state complete --timeout-ms 15000
# or wait for a specific element:
cmux browser surface:7 wait --selector "#ready" --timeout-ms 10000

# Inspect:
cmux browser surface:7 snapshot --interactive
cmux browser surface:7 get text body
cmux browser surface:7 screenshot --out /tmp/preview.png

# Interact (refs come from snapshot --interactive):
cmux browser surface:7 fill e1 "hello"
cmux --json browser surface:7 click e2 --snapshot-after
```

Alternatives for opening a URL:
- `cmux new-pane --type browser --direction right --url http://localhost:5173`
  — opens a browser pane split alongside the current one.
- `cmux open http://localhost:5173` — opens in a preview tab in the current
  pane's pane (HTML opens in a browser split without focus by default).

**Browser surfaces target the caller's workspace** (`CMUX_WORKSPACE_ID`) even
when another workspace is focused. Override with `--workspace`/`--window`.

**Refs go stale.** Re-snapshot after navigation, modal open/close, or major DOM
changes. Use `--snapshot-after` on mutating actions to get a fresh snapshot in
one call. See `references/commands.md` for the full browser command map and the
official `cmux-browser` skill (`cmux docs browser`) for deep patterns (auth,
session state, viewport emulation).

## Workflow C — parallel work in its own surface

For short-lived parallel work you want to watch alongside your main pane: split
the current pane and send a command to the new surface.

```bash
# Split the current pane to the right; returns the new surface/pane ref.
cmux new-split right
# (defaults to $CMUX_SURFACE_ID; --focus false keeps you where you are)

# Send a command to the new surface (resolve its ref from new-split output,
# or via cmux list-pane-surfaces):
cmux send --surface surface:8 "npm test\n"

# Read its result without leaving your pane:
cmux read-screen --surface surface:8 --scrollback --lines 50

# Or move an existing surface into its own split without changing focus:
cmux split-off --surface surface:4 right

# Reorder / move surfaces between panes:
cmux move-surface --surface surface:4 --pane pane:2 --focus true
cmux reorder-surface --surface surface:4 --after surface:1
```

For work that should be fully isolated (different cwd, separate todos, own
workspace tab), use `new-workspace` (Workflow A pattern) instead of a split.

## Workflow D — launch a peer agent in its own surface

When parallel work is itself an agent session (a second coding agent on a
different task, a reviewer, a researcher), give it its own surface so it has
isolated cwd, output, and lifecycle. Two ways:

**1. Agent-session surface (first-class).** cmux has a native surface type for
agent sessions — it wires session-restore and the Feed permission bridge
automatically:

```bash
# Create an agent-session surface. --provider selects the agent CLI;
# --working-directory sets the cwd. Renderer defaults to react.
cmux new-surface --type agent-session --provider codex \
  --working-directory ~/projects/myapp --focus true
```

**2. Bare command in a new workspace.** If there is no first-class provider,
create a workspace and send the agent's launch command:

```bash
cmux new-workspace --name "reviewer" --cwd ~/projects/myapp \
  --command "<the-agent-launch-command>" --focus false
```

cmux ships first-class launchers and hook integrations for common agent CLIs
that add session-restore (resume after relaunch), the Feed permission bridge
(inline approvals in the sidebar), and Agent Hibernation awareness. **Prefer
the first-class launcher when it matches the harness** — see
`references/agent-launchers.md` for the launcher commands, the hook matrix,
and how to install them (`cmux hooks setup`). The launchers are harness
coupling, so they live in that reference, not in this agnostic body.

**One surface per agent.** Do not stack multiple agent sessions in one pane's
tabs if you need to read their output concurrently — `read-screen` reads one
surface at a time. Give each agent its own surface (or workspace) and poll
them in turn.

**Agent Hibernation.** cmux can reclaim idle background agent terminals
(SIGTERM the process, swap in a placeholder, resume the session on return) to
free RAM when you exceed the live-terminal limit. It is opt-in and off by
default. Implication for an agent driving cmux: **do not assume a background
surface's process stays alive.** Make your commands re-runnable (a dev server
should restart cleanly; an agent session resumes via its saved session ID).
Visible terminals are never hibernated. See `references/agent-launchers.md`.

## Read & control any surface

The send/keys/read trio — the tmux `send-keys` / `capture-pane` equivalents:

```bash
cmux send --surface surface:2 "echo hello\n"      # \n = Enter, \t = Tab
cmux send --surface surface:2 "ls -la"             # no Enter — append only
cmux send-key --surface surface:2 ctrl+c           # one key event
cmux send-key --surface surface:2 enter
cmux read-screen --surface surface:2               # visible viewport
cmux read-screen --surface surface:2 --scrollback --lines 200  # last 200 lines
cmux focus-pane --pane pane:2                      # focus a pane
cmux focus-window --window window:1                # bring a window to front
cmux trigger-flash --surface surface:7            # visual attention cue on a surface
```

Key names follow terminal conventions: `enter`, `tab`, `escape`, `ctrl+c`,
`ctrl+d`, `up`/`down`/`left`/`right`, `space`. For browser surfaces use the
browser verbs (`click`, `fill`, `press`) instead of `send`/`send-key`.

**Read before you send.** Always `read-screen` a surface before sending to it,
to confirm the shell is at a prompt and not mid-command. Sending `ctrl+c` to a
surface that is already idle is harmless; sending a command to a surface
mid-build corrupts its state.

## Live docs, status, and notifications

cmux surfaces are not just terminals — they carry per-workspace state an agent
can drive:

```bash
# Open a markdown file in a formatted viewer panel with live reload —
# ideal for a live PLAN.md / SPEC.md you keep updating.
cmux markdown open docs/plans/2026-07-28-feature-x/PLAN.md --direction right

# Per-workspace todo checklist (writable by agent and human):
cmux todo add "Run the integration suite" --origin agent
cmux todo list
cmux todo start 1            # 1-based index from `todo list`
cmux todo check 1
cmux todo set '[{"text":"a","state":"pending"},{"text":"b"}]'  # atomic replace

# Notify the human (falls back to nothing if cmux absent — gate it):
cmux notify --title "Build complete" --body "32/32 tests passed"

# Sidebar status pills + progress (visible while the workspace is active):
cmux set-status --text "building" --color blue
cmux set-progress --value 0.6
cmux log "step 3/5 done"
cmux clear-status
```

`cmux markdown` is the right way to surface a long artifact to the human
*inside* cmux — it live-reloads on file change, so the human watches the plan
update as you work. Prefer it over pasting a wall of text into the chat.

## Layouts

Create a workspace with a predefined split layout in one call — useful for a
fixed dev environment (editor + server + logs):

```bash
cmux new-workspace --name "dev" --cwd ~/projects/myapp --layout '{
  "direction":"horizontal","split":0.5,
  "children":[
    {"pane":{"surfaces":[{"type":"terminal","command":"vim"}]}},
    {"pane":{"surfaces":[{"type":"terminal","command":"npm run dev"}]}}
  ]
}'
```

Layout surfaces define their own `command` (sent on creation). Per-workspace
environment variables: `--env KEY=VALUE` (repeatable) or `--env-file <path>`.

Workspace lifecycle verbs: `cmux workspace list|create|close|rename|select|
status|reconnect|disconnect`. `workspace status` reads/pins the todo lane
(`todo|working|needs-attention|review|done|auto`).

## When to stop

- The long-lived process is confirmed up (its port/message appears in
  `read-screen` output).
- The localhost URL opens and `browser get url` returns the expected path.
- Each peer agent / parallel task has its own surface ref recorded.
- You have read back output proving the work happened — never claim a server is
  running or a test passed from the launch command alone; `read-screen` is the
  evidence.
- Background surfaces you no longer need are closed (`workspace close`) or
  stopped (`send-key ctrl+c`) — don't orphan processes.

## Boundaries

**MUST**
- Gate every cmux call on `command -v cmux` — the agent may run outside cmux.
- Run `cmux identify --json` first to learn your own surface, then target
  *other* surfaces explicitly. Never send to `$CMUX_SURFACE_ID` blindly when
  you meant a different pane.
- `read-screen` before you `send` — confirm the target is at a prompt.
- Capture and reuse the ref that `new-workspace`/`new-split`/`browser open`
  prints. Do not hardcode `surface:2`.
- Treat cmux output as evidence: a server is "up" only when `read-screen` shows
  its ready line; a test "passed" only when `read-screen` shows the summary.

**MUST NOT**
- Do not block the session on a long-lived foreground command. Start it in a
  surface and poll. If a command genuinely must run to completion inline, cap
  the timeout and fall back to a surface on timeout.
- Do not assume a background surface's process stays alive — Agent Hibernation
  may reclaim idle ones. Make launch commands re-runnable.
- Do not name a specific harness, model, or tool in the launch command unless
  you are using a cmux first-class launcher (see `references/agent-launchers.md`).
  The skill is agnostic; the adapter picks the binary.
- Do not open a browser surface for a URL that isn't local without the human's
  ask — browser surfaces are for localhost preview and the human's explicit
  navigation, not for the agent to browse the web unsupervised.
- Do not edit `~/.config/cmux/cmux.json` without backing it up first (copy to a
  timestamped `.bak`). Use `cmux reload-config` after editing. Terminal
  rendering (font/theme/opacity) belongs in Ghostty config, not cmux settings.

## References

| File | When to load |
|------|--------------|
| `references/topology.md` | Handle model depth, identify/tree/list, focus/move/reorder/split-off, workspace lifecycle |
| `references/workflows.md` | Full worked workflows A–D with pitfalls, polling loops, and error recovery |
| `references/commands.md` | Quick-reference command tables: topology, send/read, browser, notify, todo, markdown, layout |
| `references/agent-launchers.md` | Harness-specific: first-class launchers, the hook matrix, Feed, Agent Hibernation config |

Authoritative external sources (fetch with the curl commands `cmux docs <topic>` prints):

- `cmux docs api` — CLI/socket contract, handle model, full command list
- `cmux docs agents` — agent hook integrations, Feed, session restore
- `cmux docs browser` — browser automation skill + command reference
- `cmux docs settings` — cmux.json schema, paths, reload flow
