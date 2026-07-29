# Topology — sessions, workspaces, tabs, panes, and agents

Depth on the herdr target model. The `SKILL.md` covers the patterns; this is
the reference for exact ID syntax, discovery, lifecycle, and layout.

## The hierarchy

```
session        persistent server namespace (default or named via --session)
└── workspace    top-level project container (one per repo/task)
    └── tab        a layout inside a workspace (agents, logs, server, review)
        └── pane      a real terminal (PTY), splittable right or down
            └── agent    a recognized coding-agent process with lifecycle state
```

- A **session** is a persistent server namespace with its own socket and
  runtime state. The default session is what `herdr` attaches to. Named
  sessions (`herdr --session work`, `herdr session attach work`) are separate
  runtime namespaces.
- A **workspace** is the unit of "a project context" — it has tabs, panes,
  and a sidebar rollup of agent states. One per repo, task, or investigation.
- A **tab** is a layout inside a workspace — separate views (agents, logs,
  server, review). Addressable from CLI and socket API.
- A **pane** is a real terminal (PTY). Splittable right or down. Renamable,
  readable, closable. Preserves its process across detach.
- An **agent** is a process herdr recognizes inside a pane. States:
  `blocked` | `working` | `done` | `idle` | `unknown`.

## Client/server architecture

herdr runs as a background server (owns PTYs and process state) plus one or
more attached clients (terminal UI). Detach with `ctrl+b q`; server and agents
keep running. Reattach with `herdr` or `herdr session attach <name>`.

## IDs

| Entity | ID format | Notes |
|--------|-----------|-------|
| Session | named or default | `--session <name>` or `HERDR_SESSION` env |
| Workspace | `w1` | Parse from JSON; never derive from sidebar order |
| Tab | `w1:t1` | |
| Pane | `w1:p1` | `--current` targets the calling pane |
| Agent | by name or pane ID | Names match `[a-z][a-z0-9_-]{0,31}`, unique among live agents |

All commands accept `--json` for machine-readable output. Parse IDs from the
JSON response — never hardcode `w1:p1`.

## Discovery

```bash
herdr status                        # server + client runtime status
herdr status server                 # server only
herdr status client                 # client only
herdr session list [--json]         # sessions
herdr workspace list                # workspaces in the session
herdr workspace get <id>            # one workspace's details + root pane
herdr tab list [--workspace <id>]   # tabs in a workspace
herdr tab get <id>
herdr pane list [--workspace <id>]  # panes in a workspace
herdr pane current [--current]      # the calling pane's ID
herdr pane get <id>
herdr pane layout [--current]       # pane's layout/geometry
herdr pane process-info [--current] # foreground process info
herdr pane neighbor --direction left|right|up|down [--current]
herdr pane edges [--current]        # pane's edge boundaries
herdr agent list                    # all recognized agents + states
herdr agent get <target>            # one agent's state + details
```

## Environment variables (caller context)

| Variable | Purpose |
|----------|---------|
| `HERDR_ENV` | `1` inside herdr-managed pane processes (guardrail) |
| `HERDR_PANE_ID` | Public pane ID for the running pane |
| `HERDR_TAB_ID` | Public tab ID |
| `HERDR_WORKSPACE_ID` | Public workspace ID |
| `HERDR_SOCKET_PATH` | Socket path override |
| `HERDR_SESSION` | Select a named session for CLI commands |
| `HERDR_CONFIG_PATH` | Override config file path |
| `HERDR_BIN_PATH` | Running herdr binary path |
| `HERDR_LOG` | Log filter (e.g. `HERDR_LOG=herdr=debug`) |
| `HERDR_DISABLE_SOUND` | Disable sound playback |

## Creating — sessions, workspaces, tabs, panes

```bash
# Session (attach or create)
herdr                              # default session (launches TUI — don't run from scripts)
herdr --session work               # named session (launches TUI)
herdr session attach <name>        # attach to a named session

# Workspace (also creates first tab + root pane)
herdr workspace create [--cwd PATH] [--label TEXT] [--env KEY=VALUE] [--focus|--no-focus]
# Returns: .result.workspace.workspace_id, .result.tab.tab_id, .result.root_pane.pane_id

herdr workspace focus <id>
herdr workspace rename <id> <label>
herdr workspace close <id>

# Tab
herdr tab create [--workspace <id>] [--cwd PATH] [--label TEXT] [--env KEY=VALUE] [--focus|--no-focus]
herdr tab focus <id>
herdr tab rename <id> <label>
herdr tab close <id>

# Pane (split)
herdr pane split [<id>|--pane ID|--current] --direction right|down
                 [--ratio FLOAT] [--cwd PATH] [--env KEY=VALUE] [--focus|--no-focus]
# Returns: .result.pane.pane_id
```

Split geometry rule: wide pane → split `right`; narrow/tall pane → split
`down`. Avoid repeated same-direction splits (creates thin slivers).

## Moving, swapping, zooming, resizing

```bash
# Focus a neighbor by direction
herdr pane focus --direction left|right|up|down [--current]

# Resize a pane
herdr pane resize --direction left|right|up|down [--amount FLOAT] [--current]

# Zoom (fullscreen toggle)
herdr pane zoom [<id>|--current] [--toggle|--on|--off]

# Swap (same-tab only, preserves split shape + ratios + pane IDs + processes)
herdr pane swap --direction left|right|up|down [--current]
herdr pane swap --source-pane ID --target-pane ID

# Move a pane to a different tab or workspace (keeps terminal alive, new pane ID)
herdr pane move <id> --tab <tab_id> --split right|down [--target-pane ID] [--ratio FLOAT] [--focus|--no-focus]
herdr pane move <id> --new-tab [--workspace ID] [--label TEXT] [--focus|--no-focus]
herdr pane move <id> --new-workspace [--label TEXT] [--tab-label TEXT] [--focus|--no-focus]

# Rename / close
herdr pane rename <id> <label>|--clear
herdr pane close <id>
```

## Layout export/apply (declarative)

```bash
# Export a tab's layout as a portable BSP tree.
herdr ... layout export ...   # via socket API: layout.export

# Apply a BSP tree to create a tab from it.
herdr ... layout apply ...    # via socket API: layout.apply
```

`layout.export`/`layout.apply` restore structure, labels, cwd, env, and
optional commands — but not live PTYs or scrollback. Use for reproducible
dev environments. `layout.set_split_ratio` adjusts a split ratio in place.

## Session state and restore

Multiple persistence tiers:

| Tier | What it restores | When |
|------|-----------------|------|
| **Live persistence** | Everything (processes never stop) | Detach/reattach — server keeps running |
| **Snapshot restore** | Workspace/tab/pane shape, cwd, layout, focus | Server restart — processes are gone, panes come back as new shells |
| **Pane screen history** | Recent terminal contents | Server restart, experimental (`[experimental].pane_history = true`) |
| **Native agent session restore** | Agent sessions resume with `--resume`/`--session` | Server restart, enabled by default (`[session].resume_agents_on_restore`) |
| **Live handoff** | Live panes transferred old→new server | Update, experimental (`herdr update --handoff`) |

## Remote access

Three paths:

1. **SSH to the machine, run `herdr` there** — simplest, works like tmux,
   works from phone SSH clients.
2. **`herdr --remote <host>`** — thin local client, streams UI over SSH,
   local clipboard bridging. `--remote-keybindings server` uses the server's
   keybindings. `--handoff` for live handoff.
3. **Phone SSH client** — TUI adapts to narrow screens, no mobile app needed.

## The socket API (advanced)

Newline-delimited JSON over a local Unix domain socket (or Windows named pipe).

```bash
herdr api schema              # socket protocol schema summary
herdr api schema --json       # full JSON Schema
herdr api schema --output <path>
```

Socket paths:
- `~/.config/herdr/herdr.sock` (default)
- `~/.config/herdr/sessions/<name>/herdr.sock` (named sessions)

Full method list uses dot notation: `workspace.create`, `tab.list`,
`pane.split`, `pane.send_text`, `pane.read`, `pane.wait_for_output`,
`agent.list`, `agent.start`, `agent.prompt`, `agent.wait`, `events.subscribe`,
`layout.export`, `layout.apply`, etc. Response shapes are JSON-RPC-style:
`{ "id": "req_1", "result": { "type": "pane_info", ... } }` with error shape
`{ "id": "req_1", "error": { "code": "not_found", "message": "..." } }`.

Event subscriptions: `workspace.*`, `tab.*`, `pane.*` (including
`pane.agent_status_changed`, `pane.agent_detected`, `pane.output_matched`,
`pane.scroll_changed`), `layout.updated`, `worktree.*`.

The CLI is the preferred interface for an agent (stable output, scriptable).
Reach for the socket API only when a verb has no CLI surface or you need event
subscriptions.
