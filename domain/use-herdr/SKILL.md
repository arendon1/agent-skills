---
name: use-herdr
description: |
  Drive the herdr agent multiplexer from an agent session: give each
  long-lived process (dev server, build watcher, test runner) its own pane,
  run parallel work in dedicated panes/tabs/workspaces, launch peer agent
  sessions with isolated cwd/output/lifecycle, send commands, read output,
  wait on agent state changes, and signal completion via notifications.
  Cross-platform (Linux, macOS, Windows) — the portable alternative to
  cmux when you are not on macOS or not inside a cmux terminal.
  Use when the agent must run a long-lived process in a dedicated pane,
  preview a localhost URL (by opening a browser pane in the terminal),
  give a parallel task or peer agent its own pane, monitor or control a
  pane's output, wait on another agent's state, manage terminal topology
  across sessions/workspaces/tabs/panes, coordinate multiple agent
  sessions that each need their own terminal, or check out a git worktree
  as a workspace for parallel branch work.
invocation: auto
layer: domain
provides: [terminal-topology]
language: en-US
metadata:
  version: "1.0.0"
---

# use-herdr

Domain capability for terminal topology control via the `herdr` CLI. herdr
is an agent multiplexer — a single Rust binary that runs inside your existing
terminal (no Electron, no desktop app) and provides persistent terminal
workspaces with agent awareness. Cross-platform: Linux, macOS, Windows. An
agent running inside a herdr pane can create, target, and drive other panes
programmatically, wait on peer agent state, and coordinate multiple agent
sessions — all through a CLI backed by a Unix-socket (or Windows named-pipe)
API.

**When to prefer herdr over cmux:** herdr runs anywhere your terminal and SSH
do (Linux, macOS, Windows). cmux is a macOS-only desktop app. When the agent
is not on macOS or not inside a cmux terminal, herdr is the portable path.
Both skills provide `terminal-topology`; the harness picks the one whose CLI
is available.

**Canonical source:** `herdr --help` and group-level help (`herdr agent`,
`herdr pane`, `herdr workspace`, etc.) are authoritative for the installed
version. The docs site (https://herdr.dev/docs/) and the repo
(https://github.com/ogulcancelik/herdr) carry the full reference. herdr
publishes its own agent skill file (`SKILL.md` at the repo root) — read it
via `npx skills add ogulcancelik/herdr --skill herdr -g` when this skill's
references are insufficient.

## The model

```
session        persistent server namespace (default or named via --session)
└── workspace    top-level project container (one per repo/task)
    └── tab        a layout inside a workspace (agents, logs, server, review)
        └── pane      a real terminal (PTY), splittable right or down
            └── agent    a recognized coding-agent process with lifecycle state
```

- **Session → workspace → tab → pane → agent.** A pane is a real terminal; an
  agent is a recognized coding-agent process inside a pane with semantic state
  (`blocked` | `working` | `done` | `idle` | `unknown`).
- **IDs.** Workspaces: `w1`. Tabs: `w1:t1`. Panes: `w1:p1`. Agents: referenced
  by unique live name or by pane ID. Parse IDs from JSON responses — never
  derive from sidebar order or examples.
- **Caller context.** Every herdr pane exports `HERDR_ENV=1`, `HERDR_PANE_ID`,
  `HERDR_TAB_ID`, `HERDR_WORKSPACE_ID`, `HERDR_SOCKET_PATH`. Most commands
  accept `--current` to target the calling pane.

Discover where you are and what exists:

```bash
herdr status                       # server + client runtime status
herdr session list [--json]        # sessions
herdr workspace list               # workspaces
herdr tab list [--workspace w1]    # tabs in a workspace
herdr pane list [--workspace w1]   # panes in a workspace
herdr pane current --current       # the calling pane's ID
herdr agent list                   # recognized agents and their states
```

## Prerequisite: are you inside herdr?

herdr's own guardrail — only operate herdr from inside a herdr-managed pane:

```bash
test "${HERDR_ENV:-}" = 1 || { echo "not inside herdr"; exit 1; }
```

If `HERDR_ENV` is not `1`, you are not inside a herdr pane. You can still run
herdr CLI commands if the binary is on PATH and a server is running (they talk
to the socket), but `--current` is undefined — pass explicit pane/workspace IDs.

Always gate on the binary too (the agent may run outside herdr):

```bash
command -v herdr >/dev/null 2>&1 || { echo "no herdr"; exit 1; }
```

**Never run bare `herdr`** — it launches the interactive TUI. Always use a
subcommand.

## Core principle — one pane per long-lived process

The same rule as any terminal multiplexer: **give each long-lived or parallel
process its own pane.** A dev server, a build watcher, a test runner, a peer
agent, a log tail — each gets a dedicated pane with its own cwd, output
buffer, and lifecycle. You start it once, leave it running, and read its
output with `pane read` or wait on it with `pane wait-output` instead of
blocking the session on a foreground command with a giant timeout.

herdr's edge over plain polling: `pane wait-output` and `agent wait` are
server-owned, event-driven waits — no sleep loops, no missed transitions.

## Workflow A — run a dev server in a dedicated pane

```bash
# 1. Create an isolated workspace for the server (also creates first tab + root pane).
#    Parse the root pane ID from JSON output.
WS=$(herdr --json workspace create --cwd ~/projects/myapp --label "dev-server" --no-focus \
      | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["workspace"]["workspace_id"])')
PANE=$(herdr --json workspace get "$WS" \
       | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["root_pane"]["pane_id"])')

# 2. Start the server in that pane. `pane run` sends text + Enter atomically.
herdr pane run "$PANE" "npm run dev"

# 3. Wait for the ready line (server-owned, event-driven — no polling loop).
herdr pane wait-output "$PANE" --match "Local:" --source recent-unwrapped --timeout 30000

# 4. Read the tail to grab the port.
herdr pane read "$PANE" --source recent-unwrapped --lines 20

# 5. Watch logs on demand without switching focus.
herdr pane read "$PANE" --source recent --lines 200

# 6. Stop the server (send Ctrl-C to its pane).
herdr pane send-keys "$PANE" ctrl+c

# 7. Close the workspace when done.
herdr workspace close "$WS"
```

Why a *workspace* and not a *split*: a dev server is long-lived and noisy; a
separate workspace keeps it out of your editing pane's scrollback. Use a split
(Workflow C) only for short-lived parallel work you want to watch alongside.

**Capture IDs from creation responses.** `workspace create` returns
`.result.workspace.workspace_id`, `.result.tab.tab_id`, `.result.root_pane.pane_id`.
`pane split` returns `.result.pane.pane_id`. Parse them from `--json` output;
do not assume IDs stay stable.

**`pane wait-output` instead of polling.** `--match <text>` or `--regex <pat>`
with `--source recent-unwrapped` (best for logs — no soft wrapping) and
`--timeout MS`. It blocks until the text appears or the timeout hits. This is
the herdr-native way to know a server is up without a sleep loop.

## Workflow B — open a localhost webapp (browser in a pane)

herdr does not have a built-in browser surface like cmux's WKWebView panes.
To preview a localhost webapp, open the URL in the host's browser from a
herdr pane:

```bash
# From any pane, open the URL in the host's default browser.
herdr pane run "$PANE" "open http://localhost:5173"        # macOS
herdr pane run "$PANE" "xdg-open http://localhost:5173"    # Linux
herdr pane run "$PANE" "start http://localhost:5173"       # Windows (cmd)
```

For automated verification (DOM inspection, screenshots), use a headless
browser tool or a curl-based smoke test from a dedicated pane:

```bash
# Split a pane for the smoke test, run it, wait for the server, read the result.
TEST_PANE=$(herdr --json pane split --current --direction down --no-focus \
            | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
herdr pane run "$TEST_PANE" "curl -sS http://localhost:5173 | head -20"
herdr pane read "$TEST_PANE" --source recent-unwrapped --lines 30
```

If you need full browser automation (snapshot, click, fill, screenshot), run a
Playwright/Puppeteer script in a pane, or defer to a browser-automation
capability. herdr's strength is terminal topology, not browser DOM control.

## Workflow C — parallel work in its own pane

For short-lived parallel work you want to watch alongside your main pane: split
and run.

```bash
# Split the current pane. Geometry rule: wide pane -> split right; tall -> down.
# Returns the new pane ID.
P2=$(herdr --json pane split --current --direction right --no-focus \
      | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')

# Run a command in the new pane.
herdr pane run "$P2" "npm test 2>&1 | tee /tmp/test.log"

# Wait for the test result line.
herdr pane wait-output "$P2" --regex "(passed|failed|[0-9]+ tests)" \
      --source recent-unwrapped --timeout 120000

# Read the full result.
herdr pane read "$P2" --source recent-unwrapped --lines 200

# Move a pane to a new tab or workspace when it outgrows a split.
herdr pane move "$P2" --new-tab --label "tests" --no-focus
herdr pane move "$P2" --new-workspace --label "test-suite" --no-focus
```

For fully isolated parallel work (different cwd, separate context), use a new
workspace (Workflow A pattern) or a git worktree (Workflow E).

## Workflow D — launch a peer agent in its own pane

herdr is agent-first: agents are recognized runtime objects with semantic
state. Launching a peer agent is a first-class operation.

```bash
# 1. Split a pane for the peer agent (must be an available shell — no foreground
#    command/editor/agent running in it).
PANE=$(herdr --json pane split --current --direction right --no-focus \
       | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')

# 2. Start the agent in that pane. --kind selects the agent CLI; the command
#    returns only after the agent is ready for input.
herdr agent start reviewer --kind codex --pane "$PANE"

# 3. Prompt the agent and wait for it to settle (idle/done/blocked).
herdr agent prompt reviewer "Review the auth module in src/auth/" --wait --timeout 300000

# 4. Read its output.
herdr agent read reviewer --source recent-unwrapped --lines 200

# 5. Wait on its state without reading (event-driven, no polling).
herdr agent wait reviewer --until done --timeout 600000

# 6. Focus its pane when the human needs to see it.
herdr agent focus reviewer
```

**Supported `--kind` values:** `pi`, `claude`, `codex`, `gemini`, `cursor`,
`devin`, `agy`, `cline`, `omp`, `mastracode`, `opencode`, `copilot`, `kimi`,
`kiro`, `droid`, `amp`, `grok`, `hermes`, `kilo`, `qodercli`, `maki`.

**Agent names** must match `[a-z][a-z0-9_-]{0,31}` and be unique among live
agents. Target an agent by its name or by its pane ID.

**`agent prompt --wait`** atomically submits text + Enter and waits for the
first settled state (idle/done/blocked). Add `--until` for specific-state
workflows (e.g. `--until done --until blocked`). Stalled detection returns
`agent_prompt_stalled` after 5s. This is the race-free way to drive a peer
agent — no submit-then-poll gap.

**`agent wait`** is server-owned and event-driven: it pins the resolved pane
occupant so a replacement cannot satisfy the wait. Use it to block until a
peer reaches a state without reading its output in a loop.

**Alternate-screen caveat:** some TUI-based agents use an alternate-screen
buffer. If `agent read --lines N` returns no additional text, ask the agent
to write its output to a temp file and read that file instead.

For harness-specific integration hooks (lifecycle authority, session restore),
see `references/agent-integrations.md`.

## Workflow E — git worktree as a workspace (parallel branch work)

herdr's unique strength: check out a git worktree as a workspace in one call —
ideal for parallel branch work without clobbering the main checkout.

```bash
# Create a worktree on a new branch and open it as a workspace.
herdr worktree create --cwd ~/projects/myapp --branch fix/auth --label "auth-fix" --focus

# List worktrees grouped by parent repo.
herdr worktree list --cwd ~/projects/myapp --json

# Open an existing worktree as a workspace.
herdr worktree open --cwd ~/projects/myapp --path ~/projects/myapp-worktrees/fix-auth

# Remove a worktree workspace (and the git worktree).
herdr worktree remove --workspace w2 --force
```

Checkouts go under `<worktrees.directory>/<repo>/<branch-slug>` (configured in
`config.toml` under `[worktrees]`). Worktree workspaces are grouped with the
parent repo in the sidebar.

## Read & control any pane

The send/run/read/wait quartet — herdr's tmux `send-keys` / `capture-pane`
equivalents, plus event-driven wait:

```bash
herdr pane run <pane> "<command>"               # text + Enter, atomic
herdr pane send-text <pane> "<text>"            # text only, no Enter
herdr pane send-keys <pane> <key> [key ...]     # key events
herdr pane read <pane> --source visible         # current viewport
herdr pane read <pane> --source recent-unwrapped --lines 200  # last 200 lines, no soft wrap
herdr pane wait-output <pane> --match "ready" --source recent-unwrapped --timeout 30000
herdr pane focus --direction right              # focus neighbor
herdr pane zoom <pane> --toggle                 # fullscreen toggle
herdr pane close <pane>
```

Key syntax: `enter`, `tab`, `esc`, `backspace`, `left`, `right`, `up`, `down`,
`ctrl+h`, `control+j`, `alt+x`, `shift+tab`, `f1`, `minus`, `plus`, `backtick`.

**Read sources:**
- `visible` — current viewport.
- `recent` — recent scrollback with wrapping.
- `recent-unwrapped` — no soft wrapping (best for logs/grep).
- `detection` — bottom-buffer snapshot used by agent detection.

**Read before you send.** Always `pane read` before `pane run`/`send-keys` to
confirm the shell is at a prompt and not mid-command.

## Agent state & coordination

herdr tracks agent lifecycle state — the foundation for multi-agent coordination:

```bash
herdr agent list                     # all agents + states
herdr agent get <target>             # one agent's state + details
herdr agent read <target>            # read an agent's pane output
herdr agent wait <target> --until done --timeout 600000   # event-driven wait
herdr agent focus <target>           # focus the agent's pane
herdr agent attach <target>          # direct-attach to one agent terminal
herdr agent explain <target> --json  # structured state explanation
herdr agent rename <target> "name"   # rename for clarity
herdr agent send-keys <target> <key> # send a key to an agent
```

States: `blocked` (needs input/approval), `working` (actively running), `done`
(finished, not yet seen), `idle` (ready, tab seen), `unknown` (present but
unclassified). `blocked` detection is deliberately strict — unknown prompts
show as `idle` (safe, won't trigger destructive action).

**Coordinate multiple agents:** start several in sibling panes, then
`agent wait` on each in turn or check `agent list` for a rollup. The sidebar
rolls agent states up per workspace — a human can see at a glance which agents
are blocked across all projects.

## Notifications

```bash
herdr notification show "Build complete" --body "32/32 tests passed" --sound done
herdr notification show "Approval needed" --body "Peer agent waiting" --sound request --position top-right
```

Positions: `top-left`, `top-right`, `bottom-left`, `bottom-right`. Sounds:
`none`, `done`, `request`. Notification delivery is configured in `config.toml`
under `[ui]` (toast delivery: `herdr`/`terminal`/`system`/`off`).

## Config

`~/.config/herdr/config.toml` (Linux/macOS) or `%APPDATA%\herdr\config.toml`
(Windows). Print the default: `herdr --default-config`. Reload without restart:
`herdr server reload-config`.

Key sections: `[terminal]` (shell defaults, new_cwd policy), `[worktrees]`
(directory for checkouts), `[keys]` (keybindings — prefix is `ctrl+b` by
default), `[theme]` (catppuccin, tokyo-night, dracula, nord, gruvbox, …),
`[ui]` (sidebar, mouse, toast, sound), `[session]` (`resume_agents_on_restore`),
`[experimental]` (`pane_history`, `kitty_graphics`).

Before editing, back up the existing config. After editing, reload. Full config
reference: `herdr --default-config` or the docs site.

## When to stop

- The long-lived process is confirmed up (`pane wait-output` matched, or
  `pane read` shows the ready line).
- Each peer agent / parallel task has its own pane ID recorded.
- You have read back output proving the work happened — never claim a server
  is running or a test passed from the launch command alone; `pane read` is
  the evidence.
- Background panes you no longer need are closed (`pane close` / `workspace
  close`) — don't orphan processes.
- `agent wait` returned the expected terminal state (done/idle), not a timeout.

## Boundaries

**MUST**
- Gate on `HERDR_ENV=1` before using herdr from a pane; gate on `command -v
  herdr` before any herdr call.
- Never run bare `herdr` — it launches the interactive TUI. Always use a
  subcommand.
- Run `herdr pane current --current` (or parse `HERDR_PANE_ID`) first to learn
  your own pane, then target *other* panes explicitly. Use `--current` to
  target the calling pane when you mean it.
- Parse IDs from `--json` responses. Never derive IDs from sidebar order or
  examples.
- `pane read` before you `pane run`/`send-keys` — confirm the target is at a
  prompt.
- Capture and reuse the IDs that `workspace create`/`pane split`/`tab create`
  return. Do not hardcode `w1:p1`.
- Use `--no-focus` for background work so the human's focus stays put.
- Treat herdr output as evidence: a server is "up" only when `pane read` or
  `pane wait-output` confirms it; a test "passed" only when `pane read` shows
  the summary.

**MUST NOT**
- Do not block the session on a long-lived foreground command. Start it in a
  pane and use `pane wait-output` / `agent wait` (event-driven, no polling).
- Do not close panes/workspaces/sessions/tabs you did not create.
- Never run `herdr server stop` unless the human explicitly asks — it kills
  all pane processes.
- Never kill the main herdr process.
- Do not name a specific harness, model, or tool in the launch command unless
  using `herdr agent start --kind <kind>` (see `references/agent-integrations.md`
  for the kind list and integration hooks). The skill is agnostic; the adapter
  picks the binary.
- Do not run bare `herdr` from a script — it attaches the TUI and blocks.

## References

| File | When to load |
|------|--------------|
| `references/topology.md` | Session/workspace/tab/pane model, IDs, discovery, lifecycle, layout export/apply |
| `references/workflows.md` | Full worked workflows A–E with pitfalls, polling-vs-wait, and error recovery |
| `references/commands.md` | Quick-reference command tables: topology, pane send/read/wait, agent, worktree, notification, config |
| `references/agent-integrations.md` | Harness-specific: `agent start --kind` list, integration install, lifecycle-authority vs session-identity hooks, session restore commands |

Authoritative external sources:

- `herdr --help` and group help (`herdr agent`, `herdr pane`, `herdr workspace`, …)
- `herdr --default-config` — full default configuration
- `herdr api schema --json` — socket protocol JSON Schema
- https://herdr.dev/docs/ — docs site (concepts, cli-reference, socket-api, agents, configuration, plugins, session-state)
- https://github.com/ogulcancelik/herdr — repo (Rust source, docs, official `SKILL.md`)
