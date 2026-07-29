# Commands — quick reference

Compact command tables. For handle syntax and lifecycle depth see
`topology.md`; for worked sequences see `workflows.md`.

## Global options

| Option | Effect |
|--------|--------|
| `--socket <path>` | Override the socket path for this invocation |
| `--password <value>` | Explicit socket auth (overrides `CMUX_SOCKET_PASSWORD`) |
| `--window <id\|ref\|index>` | Route through a specific window |
| `--json` | Prefer machine-readable JSON output |
| `--id-format refs\|uuids\|both` | Handle format in output |

`cmux <path>` opens a directory in a new workspace (no socket needed).
`cmux [opts] <command> [opts]` runs a named command. Presentation options
(`--json`, `--id-format`) may appear before or after the command.

## Discovery / identity

```bash
cmux identify --json              # caller context — run first
cmux tree --all                  # full window>workspace>pane>surface tree
cmux list-windows                # windows
cmux current-window              # selected window ID
cmux list-workspaces             # workspaces in caller's window
cmux current-workspace           # current workspace info
cmux list-panes [--workspace W]  # panes in a workspace
cmux list-pane-surfaces [--pane P]  # surfaces in a pane
cmux top                         # process/resource usage
cmux surface-health              # surface health
cmux capabilities                # server capabilities JSON
cmux ping                        # socket connectivity
```

## Create / destroy

```bash
cmux new-window
cmux focus-window --window W
cmux close-window --window W

cmux new-workspace [--name T] [--description D] [--cwd P] [--command CMD]
                   [--env K=V]... [--env-file F]... [--layout JSON]
                   [--window W] [--focus F] [--group G] ...
cmux workspace create ...        # = new-workspace
cmux workspace close <W>
cmux workspace rename <W> --title "T"
cmux workspace select <W>

cmux new-split <left|right|up|down> [--workspace W] [--surface S] [--focus F]
cmux new-pane [--type terminal|browser] [--direction d]
              [--placement workspace|dock] [--url URL] [--focus F]
cmux new-surface [--type terminal|browser|agent-session] [--pane P]
                 [--placement workspace|dock] [--url URL]
                 [--provider codex|claude|opencode] [--renderer react|solid]
                 [--working-directory PATH] [--focus F]
cmux close-surface ... 
```

## Move / reorder / split-off

```bash
cmux move-surface --surface S [--pane P | --workspace W | --window W]
                 [--before S2 | --after S2 | --index N] [--focus F]
cmux split-off --surface S <left|right|up|down> [--focus F]
cmux reorder-surface --surface S [--before S2 | --after S2 | --index N]
cmux move-workspace-to-window ...
cmux reorder-workspace ...
cmux move-tab-to-new-workspace ...
cmux tab-action <action> [--surface S] [--title T]   # rename, new-terminal-right,
                                                      # new-browser-right, close-*, pin, ...
cmux focus-pane [--pane P]
```

## Send / read / keys (terminal surfaces)

```bash
cmux send [--surface S] [--workspace W] [--] <text>      # \n=Enter \t=Tab
cmux send-key [--surface S] [--workspace W] <key>         # enter, tab, escape,
                                                          # ctrl+c, ctrl+d, up, down, ...
cmux send-panel --panel S [--] <text>                     # alias targeting a panel
cmux send-key-panel --panel S <key>
cmux read-screen [--surface S] [--workspace W] [--scrollback] [--lines N]
```

## Browser (surfaces)

```bash
cmux browser open <url> [--workspace W] [--window W] [--focus F]   # returns surface:N
cmux --json browser open <url>                          # parse surface_ref
cmux browser <surface> goto <url> [--snapshot-after]
cmux browser <surface> back|forward|reload [--snapshot-after]
cmux browser <surface> get url|title
cmux browser <surface> get text|html body [--selector CSS]
cmux browser <surface> get value|attr|count|box|styles ...
cmux browser <surface> snapshot [--interactive|-i] [--cursor] [--compact] [--max-depth N] [--selector CSS]
cmux browser <surface> eval '<js>'
cmux browser <surface> wait [--selector CSS] [--text T] [--url-contains T] [--load-state interactive|complete] [--function JS] [--timeout-ms MS]
cmux browser <surface> click|dblclick|hover|focus|check|uncheck <sel|ref> [--snapshot-after]
cmux browser <surface> fill <sel|ref> [text]            # empty clears
cmux browser <surface> type <sel|ref> <text>
cmux browser <surface> press|key|keydown|keyup [--key K | K]
cmux browser <surface> select <sel|ref> <value>
cmux browser <surface> scroll [--selector CSS] [--dx N] [--dy N]
cmux browser <surface> screenshot [--out PATH]
cmux browser <surface> is visible|enabled|checked [--selector CSS]
cmux browser <surface> find role|text|label|placeholder|alt|title|testid|first|last|nth ...
cmux browser <surface> viewport <w> <h> | reset
cmux browser <surface> cookies get|set|clear ...
cmux browser <surface> storage local|session get|set|clear ...
cmux browser <surface> tab list|new|switch|close|<index>
cmux browser <surface> state save|load <path>
cmux browser <surface> console list|clear
cmux browser <surface> errors list|clear
cmux browser <surface> highlight <sel>
cmux browser <surface> download [wait] [--path P] [--timeout-ms MS]
cmux browser disable | enable | status
```

Browser surfaces target the caller's workspace (`CMUX_WORKSPACE_ID`) even when
another workspace is focused. Named keys follow Playwright/W3C conventions
(`Enter`, `Tab`, `Escape`, `ArrowLeft`, `Space`). Re-snapshot after navigation
or major DOM changes; use `--snapshot-after` on mutating actions.

## Notifications

```bash
cmux notify --title T [--subtitle S] [--body B] [--tab N] [--panel N]
cmux list-notifications
cmux dismiss-notification ... | --all-read
cmux mark-notification-read ... | --all
cmux open-notification ...
cmux jump-to-unread
cmux clear-notifications
```

Notification hooks (cmux.json): composable hooks receive every notification
policy as JSON on stdin, return updated JSON on stdout — filter banners,
sounds, custom commands. See `cmux docs settings` + the schema.

## Per-workspace todos

```bash
cmux todo add "text" [--state pending|in-progress|completed] [--origin user|agent]
cmux todo list                     # 1-based indexes + progress
cmux todo check|uncheck <index|id>
cmux todo start <index|id>          # in-progress
cmux todo edit <index|id> "text"
cmux todo rm <index|id>
cmux todo clear
cmux todo set ['<json>']           # atomic replace; JSON array, inline or piped on stdin
cmux todo open                     # open/focus the workspace's todo pane
# targets caller's workspace by default; --workspace W overrides. Cap 50 items.
```

## Sidebar status / progress / log

```bash
cmux set-status --text T [--color C]      # status pill
cmux clear-status
cmux list-status
cmux set-progress --value V
cmux clear-progress
cmux log "entry"
cmux clear-log
cmux list-log
cmux sidebar-state                    # dump sidebar metadata
cmux right-sidebar ...                # visibility, mode, focus, state
```

## Markdown viewer

```bash
cmux markdown open <path> [--workspace W] [--surface S] [--window W]
               [--direction left|right|up|down] [--focus F]
cmux markdown <path>                   # shorthand for open
# Live-reloads on file change. Good for surfacing PLAN.md / SPEC.md to the human.
```

## Layout (new-workspace --layout JSON)

```jsonc
{
  "direction": "horizontal",   // or "vertical"
  "split": 0.5,                // ratio
  "children": [
    { "pane": { "surfaces": [ { "type":"terminal", "command":"vim" } ] } },
    { "pane": { "surfaces": [ { "type":"terminal", "command":"npm run dev" } ] } }
  ]
}
```

## Socket / events / rpc (advanced)

```bash
cmux rpc <method> [json-params]
cmux events [--after SEQ] [--cursor-file F] [--name N]... [--category C]...
            [--reconnect] [--limit N] [--no-ack] [--no-heartbeat]
cmux auth status|login|logout
```

Event categories: `notification`, `feed`, `agent`. Event names include
`feed.item.received`, `feed.item.completed`, `agent.hook.<HookEventName>`.
Use `cmux events` to react to a peer agent's permission request or completion
without polling `read-screen`.

## Docs / config

```bash
cmux docs [settings|shortcuts|api|browser|agents|dock|sidebars]   # prints URLs + curl + useful cmds
cmux settings path | cmux-json | docs | shortcuts
cmux config doctor | check | validate | path | paths | docs | reload
cmux reload-config              # reload cmux.json + Ghostty config, refresh terminals
cmux shortcuts                  # keybinding reference
cmux themes [list|set|clear]
cmux restore-session
cmux agent-hibernation <on|off>
cmux browser-status
```

Config files:
- primary: `~/.config/cmux/cmux.json`
- legacy: `~/.config/cmux/settings.json`, `~/Library/Application Support/com.cmuxterm.app/settings.json`
- terminal rendering (font/theme/opacity/blur): `~/.config/ghostty/config`
- schema: `cmux docs settings` prints the schema URL.

Before editing `cmux.json`, copy it to a timestamped `.bak`. After editing,
`cmux reload-config` (no app restart needed).