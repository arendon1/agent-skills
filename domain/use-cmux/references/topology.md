# Topology — handles, identity, and lifecycle

Depth on the cmux target model. The `SKILL.md` covers the patterns; this is
the reference for exact handle syntax, discovery, and lifecycle verbs.

## The hierarchy

```
window            top-level macOS window (a cmux app window)
└── group         optional collapsible sidebar section ("workspace group")
    └── workspace   tab-like unit within a window
    │               - has a cwd, a set of env vars, a todo list, a status lane
    └── pane        split container in a workspace (vertical/horizontal split)
        └── surface   a tab within a pane
                      types: terminal | browser | agent-session
```

- A **group** is an optional sidebar container. It is *not* an addressable
  process holder — it only nests workspaces under a named, collapsible header.
  See "Workspace groups" below.
- A **workspace** is the unit of "a project context" — it has its own cwd,
  env, todos, and status. Humans see workspaces as tabs in the sidebar.
- A **pane** is a split region. A workspace with one pane is full-screen; split
  it to get multiple panes side by side.
- A **surface** is a tab inside a pane. A pane can hold many surfaces (tabs);
  only one is visible at a time. `send`/`read-screen` target a surface.
- A **browser surface** is a WKWebView; an **agent-session surface** is a
  first-class agent terminal with session-restore + Feed wiring.

## Workspace groups

A group nests workspaces under one collapsible sidebar row. It is purely a
human-facing organization layer: no process, no cwd of its own, no I/O verbs.
Agents use it so the workspaces they spawn do not flood the human's tab list,
and to re-find everything that belongs to one project.

**Anchor workspace.** Every group is owned by exactly one workspace, the
**anchor**. The group header in the sidebar *is* the anchor's representation —
there is no separate row for it, and clicking the header focuses the anchor's
panels. The anchor is always a **newly created** workspace (never promoted from
an existing one); its cwd is inherited from the `--cwd` flag, from the first
`--from` workspace, or from the active workspace. So a group always costs one
workspace, and its `member_workspace_refs` always includes the anchor first.

**Group identity.** A group carries `name`, `icon_symbol` (an SF Symbol,
default `folder.fill` when unset), `custom_color` (hex), `is_pinned`,
`is_collapsed`. These are independent of the anchor workspace's own title,
color, and icon even though they start seeded from it.

**Group handle.** `workspace_group:N` (or a UUID). `list --json` returns:

```json
{
  "window_ref": "window:1",
  "groups": [
    {
      "ref": "workspace_group:2",
      "name": "Universidad",
      "anchor_workspace_ref": "workspace:3",
      "member_workspace_refs": ["workspace:3", "workspace:4", "workspace:5"],
      "member_count": 3,
      "is_collapsed": false,
      "is_pinned": false,
      "custom_color": null,
      "icon_symbol": null
    }
  ]
}
```

**The tree is blind to groups.** `cmux tree --all` shows the
workspace→pane→surface hierarchy and nothing about grouping; an anchor appears
as a normal workspace (typically named `Group 1`, `Group 2`, …). Never infer
membership from the tree — `cmux workspace-group list --json` is the only
source of truth. When you want "what is in group X", map
`member_workspace_refs` back through `cmux tree --all` (or
`cmux list-workspaces`) to get titles, cwds, and surfaces.

**Membership is one group per workspace.** `Workspace.groupId` is a single
field: `workspace-group add` moves a workspace out of whatever group it was in
before, silently. There is no nesting (a group cannot contain a group), and
top-level pinned rows (workspaces *and* groups) sort above unpinned ones; within
each tier the human's drag order holds.

**Lifecycle.** Verified against cmux 0.64.22 (`cmux workspace-group --help`):

```
cmux workspace-group list [--json]
cmux workspace-group create [--name N] [--cwd P] [--from W,W,...]
                            # omit --from → anchor-only group
cmux workspace-group add --group G --workspace W     # moves W out of any prior group
cmux workspace-group remove --workspace W           # no --group needed
cmux workspace-group set-anchor --group G --workspace W
cmux workspace-group new-workspace G [--placement afterCurrent|top|end]
cmux workspace-group rename G --name N
cmux workspace-group collapse G | expand G
cmux workspace-group pin G | unpin G
cmux workspace-group set-color G [--hex '#RRGGBB']
cmux workspace-group set-icon G [--symbol sf-symbol-name]
cmux workspace-group move G --to-index n | --before G2 | --after G2
cmux workspace-group focus G            # focus the anchor workspace
cmux workspace-group ungroup G          # dissolve, keep all members
cmux workspace-group delete G           # alias of ungroup in 0.64.x
cmux workspace-group delete G --close-workspaces   # DESTRUCTIVE
cmux workspace group <subcommand>       # canonical noun alias, same verbs
```

`create` returns either the bare handle (`workspace_group:4`) or, with
`--json`, a `{ "group": { … } }` payload with the same fields as `list`.
Everything else prints `OK` / `OK workspace:N` / `OK group dissolved (kept N
workspaces)` — **`--json` is honored only by `list` and `create`**, so parse
text for the other verbs or re-run `list --json` to confirm.

**Closing the anchor — two conflicting texts.** The installed CLI help
(0.64.22) says: *"Closing the anchor closes only that workspace and promotes
the group's next member to be the new anchor, so the group and its other
members stay intact. When the anchor is the group's only workspace, the group
is removed."* The public `docs/workspace-groups.md` still says the opposite —
that closing the anchor **dissolves** the group and leaves members ungrouped,
with a confirmation dialog in the app. Treat both as untrusted: after any
anchor close, re-run `cmux workspace-group list --json` and see what actually
happened rather than assuming.

**Destruction policy for agents.** `ungroup`/`delete` (without flag) are safe:
they drop the container and keep every member as a normal workspace.
`delete --close-workspaces` kills every workspace in the group outright,
including any dev server or peer agent running inside it. Before using it,
stop each member's foreground process, read its output to confirm, and make
sure the members are workspaces *you* created.

**Creating a workspace directly into a group** (the normal agent move) uses the
workspace verb, not the group verb — full `new-workspace` flags are available:

```bash
cmux new-workspace --group workspace_group:4 --group-placement afterCurrent \
  --group-reference workspace:9 \
  --name "dev-server" --cwd ~/projects/myapp --command "npm run dev" --focus false
```

`--group-placement` defaults to `top` when driven from the CLI/group header
(there is no active in-group reference, so `afterCurrent` degenerates to `top`).
Cmd-N inside a group uses the active group workspace as reference, so the
interactive default stays `afterCurrent`. Per-cwd overrides + global default live
in `~/.config/cmux/cmux.json` under `workspaceGroups` — see
`cmux docs settings` and `cmux docs api`.

**Scope.** In 0.64.x, `workspace-group` is the shipped spelling; `cmux
workspace group …` is the canonical noun alias and the hyphenated form stays
forever. `newWorkspacePlacement`, `contextMenu` group actions, and the
iMessage-mode group knobs (`sortInsideGroups`, `floatGroups`) are documented in
the public doc as *planned/reserved* — do not rely on them.

## Handle syntax

Output defaults to **short refs**: `window:1`, `workspace:2`, `pane:3`,
`surface:4`, `tab:15`, `workspace_group:6`. UUIDs are accepted as input
everywhere a handle is taken. Request UUID output only when you need a stable
ID to log:

```
cmux <cmd> --id-format refs      # default — short refs
cmux <cmd> --id-format uuids     # UUIDs only
cmux <cmd> --id-format both      # ref + UUID
```

Indexes (bare numbers) are also accepted where a handle is expected.

## Caller context — know thyself

Every cmux terminal exports these env vars; most commands default to them:

| Env var | Meaning |
|---------|---------|
| `CMUX_WORKSPACE_ID` | The workspace the terminal belongs to |
| `CMUX_SURFACE_ID` | The surface (tab) the terminal is |
| `CMUX_TAB_ID` | The tab context for tab commands |
| `CMUX_SOCKET_PATH` | The Unix socket to talk to (override) |
| `CMUX_SOCKET_PASSWORD` | Socket auth (or `--password`) |

`cmux identify --json` prints the full caller context — your own pane/surface/
workspace/window refs, the focused surface, the socket path, and whether you
are on a browser surface. **Run it first in any session** so you can target
*other* surfaces explicitly instead of clobbering your own.

```bash
cmux identify --json
# {
#   "caller": { "pane_ref":"pane:13", "surface_ref":"surface:15",
#               "workspace_ref":"workspace:1", "window_ref":"window:1",
#               "surface_type":"terminal" },
#   "focused": { ... the currently focused surface ... },
#   "socket_path": "/Users/.../cmux.sock"
# }
```

## Discovery commands

```bash
cmux tree --all                       # full hierarchy, human-readable
cmux list-windows                     # windows
cmux current-window                   # selected window ID
cmux list-workspaces                  # workspaces in caller's window
cmux current-workspace                # current workspace info
cmux list-panes                       # panes in caller's workspace
cmux list-panes --workspace workspace:2
cmux list-pane-surfaces               # surfaces in caller's focused pane
cmux list-pane-surfaces --pane pane:1
cmux top                              # process/resource usage per pane
cmux surface-health                   # terminal surface health
cmux capabilities                     # server capabilities JSON
```

`cmux tree --all` is the fastest way to re-derive every handle at once when
you have lost track. Parse its output (or use `--json` on the list commands)
to recover refs.

## Creating — windows, workspaces, panes, surfaces

```bash
# Window
cmux new-window
cmux focus-window --window window:2
cmux close-window --window window:2

# Workspace (the rich one — cwd, command, env, layout, group)
cmux new-workspace [--name T] [--description D] [--cwd P] [--command CMD]
                    [--env KEY=VALUE]... [--env-file F]... [--layout JSON]
                    [--window W] [--focus true|false]
                    [--group G] [--group-placement afterCurrent|top|end]
# Canonical noun form (legacy verbs print a deprecation hint but still work):
cmux workspace create ...             # same flags as new-workspace

# Pane (split)
cmux new-split <left|right|up|down> [--workspace W] [--surface S] [--focus F]
cmux new-pane [--type terminal|browser] [--direction d] [--placement workspace|dock]
              [--workspace W] [--url URL] [--focus F]
#   --placement dock splits the right-sidebar Dock instead of the workspace.

# Surface (tab in a pane)
cmux new-surface [--type terminal|browser|agent-session] [--pane P]
                 [--placement workspace|dock] [--workspace W] [--url URL]
                 [--provider codex|claude|opencode]   # agent-session only
                 [--renderer react|solid]             # agent-session only
                 [--working-directory PATH] [--focus F]
```

`new-workspace --command` sends text+Enter to the first terminal after
creation. `--layout` creates a pre-split workspace whose surfaces each define
their own `command` (see SKILL.md Layouts).

## Moving, reordering, splitting off

```bash
# Move a surface to another pane/workspace/window, or to an index.
cmux move-surface --surface surface:1 --pane pane:2
cmux move-surface --surface surface:1 --workspace workspace:2 --focus true
cmux move-surface surface:1 --index 0
cmux move-surface --surface surface:1 --before surface:3

# Move a surface into a new split (no focus change by default).
cmux split-off --surface surface:1 right
cmux split-off --workspace workspace:2 --surface surface:4 down --focus true

# Reorder a surface within its pane.
cmux reorder-surface --surface surface:1 --index 0
cmux reorder-surface --surface surface:3 --after surface:1

# Reorder / move workspaces.
cmux reorder-workspace ...
cmux move-workspace-to-window ...
cmux move-tab-to-new-workspace ...

# Tab context-menu actions (tab-action accepts tab:N or surface:N):
cmux tab-action rename --surface surface:1 --title "logs"
cmux tab-action new-terminal-right
cmux tab-action new-browser-right
cmux tab-action close-others
```

## Workspace lifecycle + state

```bash
cmux workspace list
cmux workspace create ...             # = new-workspace
cmux workspace close <workspace>
cmux workspace rename <workspace> --title "new"
cmux workspace select <workspace>
cmux workspace env [<workspace>] [--mask] [--json]   # configured env vars
cmux workspace status                  # effective/inferred/override todo lane
cmux workspace status set working      # pin a lane: todo|working|needs-attention|review|done|auto
cmux workspace reconnect [<workspace>] # reconnect a remote (SSH) workspace
cmux workspace disconnect [<workspace>]
cmux workspace loading <on|off> [--id name]  # toggle the loading spinner
```

Workspace action verbs (context-menu): `pin`, `unpin`, `rename`,
`clear-name`, `set-description`, `clear-description`, `move-up`, `move-down`,
`move-top`, `close-others`, `close-above`, `close-below`, `mark-read`,
`mark-unread`, `set-color`, `clear-color` — via `cmux workspace-action`.

## Window displays

```bash
cmux window displays                   # list connected displays
cmux window display <name|index>       # move window(s) onto a display
cmux window default-display [<name>|--clear]   # dev default display
```

## The socket API (advanced)

For programmatic control beyond the CLI, cmux exposes a v2 socket API:

```bash
cmux rpc <method> [json-params]        # call a raw v2 method
cmux events [options]                  # stream events as newline-delimited JSON
cmux ping                               # check socket connectivity
```

`cmux events` is reconnectable and filterable:

```bash
cmux events --category notification
cmux events --category feed --category agent --reconnect \
  --cursor-file ~/.cache/cmux/events.seq
cmux events --name feed.item.received --limit 5
```

Use `cmux events` to observe Feed decisions, agent hook activity, and
notifications as they happen — useful for an agent that wants to react to a
peer agent's permission request or completion without polling `read-screen`.

The CLI is the preferred interface for an agent (stable text output, scriptable).
Reach for `cmux rpc` only when a verb has no CLI surface.
