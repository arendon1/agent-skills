# Commands — quick reference

Compact command tables. For handle syntax and lifecycle depth see
`topology.md`; for worked sequences see `workflows.md`.

## Global options

| Option | Effect |
|--------|--------|
| `--session <name>` | Use or create a named persistent session |
| `--remote <target>` | Attach through SSH to a remote herdr server |
| `--remote-keybindings <local\|server>` | Keybindings for `--remote` attach (default: local) |
| `--handoff` | Opt into live handoff for update or remote attach |
| `--no-session` | Run monolithically (no server/client, escape hatch) |
| `--default-config` | Print default configuration and exit |
| `--version`, `-V` | Print version and exit |
| `--help`, `-h` | Show help |

Never run bare `herdr` from a script — it launches the interactive TUI.
Always use a subcommand. All commands accept `--json` for machine-readable
output.

## Launch & status

```bash
herdr                              # launch or attach default session (TUI)
herdr --session work               # named session (TUI)
herdr --remote workbox             # remote thin client
herdr --remote workbox --remote-keybindings server
herdr --remote workbox --handoff
herdr --no-session                 # single-process escape hatch
herdr --default-config             # print default config
herdr --version                    # print version

herdr status                       # overall status
herdr status server                # server only
herdr status client                # client only
```

## Server

```bash
herdr server                       # run headless server explicitly
herdr server stop                  # stop server and pane processes
herdr server reload-config         # apply reloadable settings
herdr server agent-manifests [--json]
herdr server update-agent-manifests [--json]
herdr server reload-agent-manifests
```

## Sessions

```bash
herdr session list [--json]
herdr session attach <name>
herdr session stop <name> [--json]
herdr session delete <name> [--json]
```

## Workspaces

```bash
herdr workspace list
herdr workspace create [--cwd PATH] [--label TEXT] [--env KEY=VALUE] [--focus|--no-focus]
herdr workspace get <id>
herdr workspace focus <id>
herdr workspace rename <id> <label>
herdr workspace report-metadata <id> --source ID [--token NAME=VALUE] [--clear-token NAME] [--seq N] [--ttl-ms N]
herdr workspace close <id>
# create returns: .result.workspace.workspace_id, .result.tab.tab_id, .result.root_pane.pane_id
```

## Worktrees (Git)

```bash
herdr worktree list [--workspace ID | --cwd PATH] [--json]
herdr worktree create [--workspace ID | --cwd PATH] [--branch NAME] [--base REF] [--path PATH] [--label TEXT] [--focus|--no-focus] [--json]
herdr worktree open [--workspace ID | --cwd PATH] (--path PATH | --branch NAME) [--label TEXT] [--focus|--no-focus] [--json]
herdr worktree remove --workspace ID [--force] [--json]
```

## Tabs

```bash
herdr tab list [--workspace <id>]
herdr tab create [--workspace <id>] [--cwd PATH] [--label TEXT] [--env KEY=VALUE] [--focus|--no-focus]
herdr tab get <id>
herdr tab focus <id>
herdr tab rename <id> <label>
herdr tab close <id>
```

## Panes — inspect

```bash
herdr pane list [--workspace <id>]
herdr pane current [--pane ID|--current]
herdr pane get <id>
herdr pane layout [--pane ID|--current]
herdr pane process-info [--pane ID|--current]
herdr pane neighbor --direction left|right|up|down [--pane ID|--current]
herdr pane edges [--pane ID|--current]
```

## Panes — manipulate

```bash
herdr pane focus --direction left|right|up|down [--pane ID|--current]
herdr pane resize --direction left|right|up|down [--amount FLOAT] [--pane ID|--current]
herdr pane zoom [<id>|--pane ID|--current] [--toggle|--on|--off]
herdr pane rename <id> <label>|--clear
herdr pane split [<id>|--pane ID|--current] --direction right|down [--ratio FLOAT] [--cwd PATH] [--env KEY=VALUE] [--focus|--no-focus]
# split returns: .result.pane.pane_id

herdr pane swap --direction left|right|up|down [--pane ID|--current]
herdr pane swap --source-pane ID --target-pane ID
herdr pane move <id> --tab <tab_id> --split right|down [--target-pane ID] [--ratio FLOAT] [--focus|--no-focus]
herdr pane move <id> --new-tab [--workspace ID] [--label TEXT] [--focus|--no-focus]
herdr pane move <id> --new-workspace [--label TEXT] [--tab-label TEXT] [--focus|--no-focus]
herdr pane close <id>
```

## Panes — send / read / wait

```bash
herdr pane run <id> <command>               # text + Enter, atomic
herdr pane send-text <id> <text>            # text only, no Enter
herdr pane send-keys <id> <key> [key ...]   # key events
herdr pane read <id> [--source visible|recent|recent-unwrapped|detection] [--lines N] [--format text|ansi] [--ansi] [--raw]
herdr pane wait-output <id> (--match <text> | --regex <pattern>) [--source visible|recent|recent-unwrapped] [--lines N] [--timeout MS] [--raw]
```

Key syntax: `enter`, `tab`, `esc`, `backspace`, `left`, `right`, `up`, `down`,
`ctrl+h`, `control+j`, `alt+x`, `shift+tab`, `f1`, `minus`, `plus`, `backtick`.

Read sources:
- `visible` — current viewport
- `recent` — recent scrollback with wrapping
- `recent-unwrapped` — no soft wrapping (best for logs/grep)
- `detection` — bottom-buffer snapshot used by agent detection

## Panes — agent state reporting (custom hooks)

```bash
herdr pane report-agent <id> --source ID --agent LABEL --state idle|working|blocked|unknown [--message TEXT] [--seq N] [--agent-session-id ID] [--agent-session-path PATH]
herdr pane report-agent-session <id> --source ID --agent LABEL [--seq N] [--agent-session-id ID] [--agent-session-path PATH] [--session-start-source SOURCE]
herdr pane release-agent <id> --source ID --agent LABEL [--seq N]
herdr pane report-metadata <id> --source ID [--agent LABEL] [--applies-to-source ID] [--title TEXT|--clear-title] [--display-agent TEXT|--clear-display-agent] [--state-label STATUS=TEXT] [--clear-state-labels] [--token NAME=VALUE] [--clear-token NAME] [--seq N] [--ttl-ms N]
```

## Agents

```bash
herdr agent list
herdr agent get <target>                        # target = agent name or pane ID
herdr agent read <target> [--source visible|recent|recent-unwrapped|detection] [--lines N] [--format text|ansi] [--ansi]
herdr agent send-keys <target> <key> [key ...]
herdr agent prompt <target> <text> [--wait] [--until STATUS]... [--timeout MS]
herdr agent rename <target> <name>|--clear
herdr agent focus <target>
herdr agent wait <target> [--until STATUS]... [--timeout MS]
herdr agent attach <target> [--takeover]
herdr agent start <name> --kind KIND --pane ID [--timeout MS] [-- <agent-args...>]
herdr agent explain <target> [--json|--verbose]
herdr agent explain --file PATH --agent LABEL [--json|--verbose]
```

Agent states: `blocked`, `working`, `done`, `idle`, `unknown`.
`agent prompt --wait` default settled states: idle/done/blocked.
`agent start` kinds: see `agent-integrations.md`.

## Direct terminal attach

```bash
herdr terminal attach <terminal_id> [--takeover]
herdr terminal session control <target> [--takeover] [--cols N] [--rows N]
herdr terminal session observe <target> [--cols N] [--rows N]
herdr terminal title set <title>
herdr terminal title clear
```

Detach from direct attach: `ctrl+b q`. Send literal `ctrl+b`: `ctrl+b ctrl+b`.

## Integrations

```bash
herdr integration install <agent>
herdr integration uninstall <agent>
herdr integration status [--outdated-only]
```

See `agent-integrations.md` for the agent list and integration types.

## Plugins

```bash
herdr plugin install <owner>/<repo>[/subdir...] [--ref REF] [--yes]
herdr plugin list [--plugin ID] [--json]
herdr plugin uninstall <plugin_id|owner/repo[/subdir...]>
herdr plugin enable <plugin_id>
herdr plugin disable <plugin_id>
herdr plugin link <path> [--disabled]
herdr plugin unlink <plugin_id>
herdr plugin config-dir <plugin_id>
herdr plugin action list [--plugin ID]
herdr plugin action invoke <action_id> [--plugin ID]
herdr plugin log list [--plugin ID] [--limit N]
herdr plugin pane open --plugin ID --entrypoint ID [--placement overlay|popup|split|tab|zoomed]
                        [--width SIZE] [--height SIZE] [--workspace ID] [--target-pane PANE]
                        [--direction right|down] [--cwd PATH] [--env KEY=VALUE] [--focus|--no-focus]
herdr plugin pane focus <pane_id>
herdr plugin pane close <pane_id>
```

## Notifications

```bash
herdr notification show <title> [--body TEXT] [--position top-left|top-right|bottom-left|bottom-right] [--sound none|done|request]
```

Positions: `top-left`, `top-right`, `bottom-left`, `bottom-right`.
Sounds: `none`, `done`, `request`.

## Updates & completions

```bash
herdr update
herdr update --handoff
herdr channel show
herdr channel set preview|stable
herdr completion zsh|bash|fish|powershell|elvish
```

## Socket API / schema

```bash
herdr api schema                 # socket protocol schema summary
herdr api schema --json          # full JSON Schema
herdr api schema --output <path>
```

Socket paths: `~/.config/herdr/herdr.sock` (default),
`~/.config/herdr/sessions/<name>/herdr.sock` (named sessions).

## Config

```bash
herdr --default-config           # print default config
herdr config reset-keys          # back up config.toml + remove custom keybindings
herdr server reload-config       # reload config.toml in the running server
```

Config file: `~/.config/herdr/config.toml` (Linux/macOS),
`%APPDATA%\herdr\config.toml` (Windows).

Sections: `[terminal]`, `[worktrees]`, `[remote]`, `[keys]`, `[theme]`,
`[ui]`, `[session]`, `[experimental]`. Full config reference data at
`https://herdr.dev/docs/config-reference/` or `herdr --default-config`.
