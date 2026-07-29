# Agent integrations, kinds, hooks, and session restore

This reference covers the **harness-specific** parts of herdr: the
`agent start --kind` list, the integration types (lifecycle authority vs
session identity), agent detection, and session restore. It names harnesses
directly because that is what these features couple to. The `SKILL.md` body
stays agnostic; this file is the adapter's cheat sheet.

This file is not scanned by `skill-forge audit` (audit reads `SKILL.md` only).
It is still part of the skill and should stay accurate.

## `agent start --kind` — supported agents

`herdr agent start <name> --kind <kind> --pane <pane_id>` launches a recognized
agent in a pane. The command returns only after the agent is ready for input.

Supported `--kind` values (21):

| `--kind` | Agent |
|----------|-------|
| `pi` | Pi |
| `claude` | Claude Code |
| `codex` | Codex |
| `gemini` | Gemini CLI |
| `cursor` | Cursor Agent CLI |
| `devin` | Devin CLI |
| `agy` | Antigravity CLI |
| `cline` | Cline |
| `omp` | OMP |
| `mastracode` | MastraCode |
| `opencode` | OpenCode |
| `copilot` | GitHub Copilot CLI |
| `kimi` | Kimi Code CLI |
| `kiro` | Kiro CLI |
| `droid` | Droid (Factory) |
| `amp` | Amp |
| `grok` | Grok CLI |
| `hermes` | Hermes Agent |
| `kilo` | Kilo Code CLI |
| `qodercli` | Qoder CLI |
| `maki` | Maki |

Agent names must match `[a-z][a-z0-9_-]{0,31}` and be unique among live agents.
Pass extra args after `--`:

```bash
herdr agent start reviewer --kind codex --pane w1:p2 -- --model o3
```

## Integrations (`herdr integration install`)

Install an integration for one agent (hooks/plugins that report lifecycle
state and session identity):

```bash
herdr integration install <agent>
herdr integration uninstall <agent>
herdr integration status [--outdated-only]
```

Supported integration agents: `pi`, `omp`, `claude`, `codex`, `copilot`,
`devin`, `droid`, `kimi`, `opencode`, `kilo`, `hermes`, `qodercli`, `cursor`,
`mastracode`.

## Integration types — two tiers

| Type | Agents | Effect |
|------|--------|--------|
| **Lifecycle authority** | Pi, OMP, Kimi, OpenCode, Kilo, Hermes, MastraCode | Hook/plugin events author idle/working/blocked; no screen-detection fallback runs when the integration is actively reporting |
| **Session identity only** | Claude Code, Codex, Copilot, Devin, Droid, Qoder, Cursor | Reports the native session reference for restore; state still comes from screen detection |

Each integration writes its hook/plugin to the agent's config directory. For
example, the Pi integration writes to `~/.pi/agent/extensions/herdr-agent-state.ts`.

## Agent detection mechanism

herdr detects agents running in panes using two tiers:

1. **Lifecycle hooks (authoritative):** For agents with complete integrations
   (Pi, OMP, Kimi, Hermes, MastraCode), the installed integration is the sole
   authority for idle/working/blocked/session identity when actively reporting.
   No screen-manifest fallback runs.

2. **Screen manifests (fallback):** For agents without complete hooks (Claude
   Code, Codex, Copilot, etc.), herdr reads the live bottom-buffer screen
   snapshot and evaluates TOML manifests against it. Manifests can also match
   terminal title and OSC progress sequences.

**Blocked detection** is deliberately strict: only when the bottom-buffer
matches known approval/question/permission UI. Unknown prompts show as `idle`
(safe — won't trigger destructive action).

**Remote manifests:** herdr checks `herdr.dev` for manifest updates and
applies them without restart. Local overrides in
`~/.config/herdr/agent-detection/<agent>.toml` always win.

**State authority model:** Each pane has exactly one status authority at a
time. Integrations report via `herdr pane report-agent`. Custom labels via
`herdr pane report-metadata`.

## Session restore commands

After a server restart, herdr's native agent session restore (enabled by
default, `[session].resume_agents_on_restore`) restarts supported agents with
their saved session ID:

| Agent | Resume command |
|-------|----------------|
| Pi | `pi --session <path-or-id>` |
| OMP | `omp --resume=<path-or-id>` |
| Claude Code | `claude --resume <id>` |
| Codex | `codex resume <id>` |
| Cursor | `cursor-agent --resume <id>` |
| Copilot | `copilot --resume=<id>` |
| Devin | `devin --resume <id>` |
| Droid | `droid --resume <id>` |
| Kimi | `kimi --session <id>` |
| Qoder | `qodercli --resume <id>` |
| OpenCode | `opencode --session <id>` |
| Kilo | `kilo --session <id>` |
| Hermes | `hermes --resume <id>` |
| MastraCode | `mastracode --thread <id>` |

Disable automatic restore in `config.toml`:

```toml
[session]
resume_agents_on_restore = false
```

## Custom hooks — reporting state from your own integration

If you write a custom integration (e.g. for an in-house agent), report state
via the CLI:

```bash
# Report lifecycle state
herdr pane report-agent <pane> --source my-source --agent my-agent \
  --state working --message "running tests" --seq 1

# Report session identity (for restore)
herdr pane report-agent-session <pane> --source my-source --agent my-agent \
  --agent-session-id <id> --agent-session-path <path>

# Release authority (let another source take over)
herdr pane release-agent <pane> --source my-source --agent my-agent

# Report display-only metadata (sidebar labels, tokens)
herdr pane report-metadata <pane> --source my-source --agent my-agent \
  --title "my-agent" --display-agent "My Agent" \
  --state-label blocked="Waiting for approval"
```

`--source ID` is your integration's unique source identifier. `--seq N` is a
monotonic sequence number for ordering. State authority is per-pane — the
last report with the highest seq wins until released.

## Plugins (executable workflow packages)

Plugins are executable packages with a `herdr-plugin.toml` manifest declaring
build commands, actions, event hooks, managed panes, and link handlers.

```bash
herdr plugin install <owner>/<repo>[/subdir...] [--ref REF] [--yes]
herdr plugin link <path> [--disabled]     # local development
herdr plugin list [--json]
herdr plugin enable|disable <plugin_id>
herdr plugin uninstall <plugin_id|owner/repo>
herdr plugin action list [--plugin ID]
herdr plugin action invoke <action_id> [--plugin ID]
herdr plugin pane open --plugin ID --entrypoint ID [--placement overlay|popup|split|tab|zoomed] ...
herdr plugin log list [--plugin ID] [--limit N]
```

Plugin manifest sections: `[[build]]`, `[[actions]]` (with context:
workspace/tab/pane), `[[events]]` (e.g. `on = "worktree.created"`),
`[[panes]]` (managed terminal pane entrypoints), `[[link_handlers]]`
(URL pattern handlers). Plugins persist across restarts via `plugins.json`.

Plugin env vars: `HERDR_PLUGIN_ID`, `HERDR_PLUGIN_ROOT`,
`HERDR_PLUGIN_CONFIG_DIR`, `HERDR_PLUGIN_STATE_DIR`,
`HERDR_PLUGIN_ENTRYPOINT_ID`, `HERDR_PLUGIN_CONTEXT_JSON`,
`HERDR_PLUGIN_ACTION_ID`, `HERDR_PLUGIN_EVENT`, `HERDR_PLUGIN_EVENT_JSON`.

## Agent view (declarative sidebar filter/sort)

The built-in Agents view sidebar supports declarative filter/sort projections
via the socket API (`agent.view.set` / `agent.view.clear`). Use it to customize
how agents are displayed in the sidebar — filter by state, sort by name/workspace,
project specific fields. Not exposed as a CLI subcommand; reach via the socket
API when needed.
