# Agent launchers, hooks, Feed, and hibernation

This reference covers the **harness-specific** parts of cmux: the first-class
agent launchers, the hook integrations (session restore + Feed permission
bridge), and Agent Hibernation. It names harnesses directly because that is
what these cmux features do — they couple to a specific agent CLI. The
`SKILL.md` body stays agnostic; this file is the adapter's cheat sheet.

This file is not scanned by `skill-forge audit` (audit reads `SKILL.md` only).
It is still part of the skill and should stay accurate.

## First-class launcher commands

cmux ships top-level commands that launch an agent CLI with cmux pane
integration and hooks already wired:

| Command | What it launches |
|---------|------------------|
| `cmux claude-teams` | Claude Code with cmux/tmux-style agent team integration |
| `cmux codex-teams` | Codex with cmux-managed subagent panes |
| `cmux omo` | OpenCode with oh-my-openagent integration |
| `cmux omx` | Oh My Codex with cmux pane integration |
| `cmux omc` | Oh My Claude Code with cmux pane integration |

These are the harness-coupled entry points. An agent that wants to spawn a
peer agent with full session-restore + Feed wiring should prefer the matching
launcher over a bare `cmux new-workspace --command "..."`.

**Unifying mechanism:** all of the above use a tmux-compatibility shim
(`cmux __tmux-compat`) that intercepts the tmux commands an orchestrator
issues (`new-session`, `new-window`, `split-window`, `send-keys`,
`capture-pane`, `select-pane`, `kill-pane`, `list-panes`) and translates them
into cmux socket-API calls. So an orchestrator that expects tmux produces
real, visible cmux panes instead of hidden background processes. This is why
"subagents become native panes" — the shim materializes them. An agent
driving cmux directly (via the CLI in this skill) does not need the shim; it
is what makes the first-class launchers' subagents appear as panes.

## Agent-session surface type

`cmux new-surface --type agent-session` creates a first-class agent surface
whose lifecycle cmux tracks. `--provider` selects the agent CLI:

```bash
cmux new-surface --type agent-session --provider codex \
  --working-directory ~/projects/myapp --focus true
# providers: codex | claude | opencode
# renderer: react (default) | solid
```

## Hook integrations (`cmux hooks`)

Hooks make session-restore and the Feed permission bridge work. Install for
all supported agents whose binaries are on `PATH`:

```bash
cmux hooks setup                    # install for every supported agent on PATH
cmux hooks setup <agent>            # one agent
cmux hooks setup --agent <agent>
cmux hooks uninstall                # remove all
cmux hooks uninstall <agent>
cmux hooks <agent> install          # one agent (alternate form)
cmux hooks <agent> uninstall
cmux hooks <agent> install --yes
# OpenCode also supports project-local Feed install:
cmux hooks opencode install --project   # writes .opencode/plugins/cmux-feed.js in cwd
```

Supported agent names: `codex`, `grok`, `opencode`, `pi`, `omp`, `campfire`,
`amp`, `cursor`, `gemini`, `kiro`, `rovodev` (alias `rovo`), `copilot`,
`codebuddy`, `factory`, `qoder`. Claude Code is handled by the cmux Claude
wrapper (injected automatically when Claude Code integration is enabled in
Settings — no `hooks setup claude`).

### Integration matrix (what each agent gets)

| Agent | Binary | Installed file | Session restore | Feed bridge |
|-------|--------|----------------|-----------------|-------------|
| Claude Code | `claude` (via wrapper) | wrapper-injected settings | `claude --resume <id>` | PermissionRequest |
| Codex | `codex` | `~/.codex/hooks.json`, `~/.codex/config.toml` | `codex resume <id>` | PreToolUse, PermissionRequest telemetry |
| Grok | `grok` | `~/.grok/hooks/cmux-session.json` | `grok -r <id>` | PreToolUse |
| OpenCode | `opencode` | `~/.config/opencode/plugins/cmux-session.js`, `cmux-feed.js` | `opencode --session <id>` | plugin event bus |
| Pi | `pi` | `~/.pi/agent/extensions/cmux-session.ts` | `pi --session <id>` | tool_execution_start/end telemetry |
| OMP | `omp` | `~/.omp/agent/extensions/cmux-omp-session.ts` or `$PI_CODING_AGENT_DIR/extensions/cmux-omp-session.ts` | `omp --session <id>` | lifecycle only |
| Campfire | `campfire` | `~/.campfire/agent/extensions/cmux-campfire-session.ts` or `$CAMPFIRE_CODING_AGENT_DIR/extensions/cmux-campfire-session.ts` | `campfire --session <id>` | lifecycle + collaborative notifications |
| Amp | `amp` | `~/.config/amp/plugins/cmux-session.ts` | `amp threads continue <id>` | tab-status + lifecycle only |
| Cursor CLI | `cursor-agent` | `~/.cursor/hooks.json` | `cursor-agent --resume <id>` | beforeShellExecution |
| Gemini | `gemini` | `~/.gemini/settings.json` | `gemini --resume <id>` | PreToolUse |
| Kiro CLI | `kiro-cli` | `~/.kiro/agents/cmux.json` or `$KIRO_HOME/agents/cmux.json` | `kiro-cli chat --resume-id <id>` | preToolUse, postToolUse |
| Rovo Dev | `acli` | `~/.rovodev/config.yml` | `acli rovodev run --restore <id>` | lifecycle only |
| Copilot | `copilot` | `~/.copilot/config.json` | `copilot --resume <id>` | PreToolUse |
| CodeBuddy | `codebuddy` | `~/.codebuddy/settings.json` | `codebuddy --resume <id>` | PreToolUse |
| Factory | `droid` | `~/.factory/settings.json` | `droid --resume <id>` | PreToolUse |
| Qoder | `qodercli` | `~/.qoder/settings.json` | `qodercli --resume <id>` | PreToolUse |
| Kimi Code | `kimi` | `~/.kimi/config.toml` | not yet | PreToolUse, PostToolUse |

Session hooks write `~/.cmuxterm/<agent>-hook-sessions.json`. Each entry
stores the agent session ID, cmux workspace ID, surface ID, cwd, PID, the
lifecycle (`running` | `idle` | `needsInput` | `unknown`), and a sanitized
launch command. On app relaunch, cmux rebuilds each workspace and runs the
agent's native resume command with the saved session ID. The sanitizer drops
prompts, credentials, old session selectors, and noninteractive commands so
relaunch resumes instead of starting a new task or leaking secrets.

### Per-process disable

Each agent can have cmux hooks disabled for one process via an env var, and a
config-directory override:

| Agent | Config dir override | Disable for one process |
|-------|---------------------|--------------------------|
| Codex | `CODEX_HOME` | `CMUX_CODEX_HOOKS_DISABLED=1` |
| Grok | `GROK_HOME` | `CMUX_GROK_HOOKS_DISABLED=1` |
| OpenCode | `OPENCODE_CONFIG_DIR` | `CMUX_OPENCODE_HOOKS_DISABLED=1` |
| Pi | `PI_CODING_AGENT_DIR` | `CMUX_PI_HOOKS_DISABLED=1` |
| OMP | `PI_CODING_AGENT_DIR` (agent dir) / `PI_CONFIG_DIR` (config root) | `CMUX_OMP_HOOKS_DISABLED=1` |
| Campfire | `CAMPFIRE_CODING_AGENT_DIR` | `CMUX_CAMPFIRE_HOOKS_DISABLED=1` |
| Amp | — | `CMUX_AMP_HOOKS_DISABLED=1` |
| Cursor CLI | — | `CMUX_CURSOR_HOOKS_DISABLED=1` |
| Gemini | — | `CMUX_GEMINI_HOOKS_DISABLED=1` |
| Kiro CLI | `KIRO_HOME` | `CMUX_KIRO_HOOKS_DISABLED=1` |
| Kimi Code | `KIMI_SHARE_DIR` | `CMUX_KIMI_HOOKS_DISABLED=1` |
| Rovo Dev | — | `CMUX_ROVODEV_HOOKS_DISABLED=1` |
| Copilot | `COPILOT_HOME` | `CMUX_COPILOT_HOOKS_DISABLED=1` |
| CodeBuddy | `CODEBUDDY_CONFIG_DIR` | `CMUX_CODEBUDDY_HOOKS_DISABLED=1` |
| Factory | — | `CMUX_FACTORY_HOOKS_DISABLED=1` |
| Qoder | `QODER_CONFIG_DIR` | `CMUX_QODER_HOOKS_DISABLED=1` |

### Workspace auto-naming

When the opt-in `automation.workspaceAutoNaming` setting is enabled, turn-end
hooks drive AI naming of workspaces and tabs. Supported adapters: Claude
Code, Codex, Grok, OpenCode, Pi, OMP. Each gates on the live setting over the
socket, reuses the session store for throttle state, summarizes with that
agent's own CLI in a no-tools/isolated headless mode, and never overwrites a
name the human set.

## Feed (inline approvals)

Feed is cmux's inline surface for agent decisions. It lives in the right
sidebar (`Ctrl-4`) and the `cmux feed tui` command. It surfaces three things
that need a human response:

- **Permission requests** — an agent wants to run a tool, edit a file, or run a
  shell command. Pick Once / Always / All tools / Bypass / Deny.
- **ExitPlanMode** — an agent finished planning and is ready to edit. Pick
  Ultraplan / Manual / Auto.
- **AskUserQuestion** — an agent asks a multiple-choice question. Pick and
  submit.

Agents pipe hook events into `cmux hooks feed --source <agent>`, which forwards
to the cmux socket as a `feed.push` V2 frame. Decisions return via
`feed.permission.reply` / `feed.question.reply` / `feed.exit_plan.reply`. All
events append to `~/.cmuxterm/workstream.jsonl` for audit (2000 in memory, older
in the JSONL log).

Permission modes sent back to the agent:

| Mode | Meaning |
|------|---------|
| Once | Allow once through the agent's native permission hook |
| Always | Allow + apply the agent's suggested persistent permission rule |
| All tools | Allow + apply the suggested persistent rule |
| Bypass | Allow + request session-level bypass (when the agent supports it) |
| Deny | Deny through the agent's native permission hook |

For Claude Code, the cmux wrapper launches with `--allow-dangerously-skip-
permissions` so a later `PermissionRequest` can switch the session into
`bypassPermissions`; without that flag Claude ignores `setMode: bypass`.

An agent that is *driving* cmux should not auto-approve on a peer's behalf.
If a peer agent's permission request is urgent and the human is away, surface
it via `cmux notify`; let the human use Feed to decide.

## Agent Hibernation

Agent Hibernation kills idle background agent processes to free RAM/CPU, then
resumes each one with its saved session when you return to its tab. Opt-in,
off by default.

```bash
cmux agent-hibernation on
cmux agent-hibernation off
```

Or in `~/.config/cmux/cmux.json`:

```json
{
  "terminal": {
    "agentHibernation": {
      "enabled": true,
      "idleSeconds": 5,
      "maxLiveTerminals": 12
    }
  }
}
```

- `idleSeconds` (default 5, range 5–604800): how long a background idle agent
  terminal must be quiet before it can hibernate.
- `maxLiveTerminals` (default 12, range 1–256): how many live restorable agent
  terminals to keep before cmux hibernates the oldest idle background ones.
- `confirmationSeconds` (~60s): the settle window during which output + process
  must stay unchanged before the kill.

A terminal is a hibernation candidate only when ALL hold: it has a saved
restorable agent session + a buildable resume command; lifecycle is `idle`
(not running, not waiting on input); the terminal is in the background (panel
not visible); live restorable terminals exceed `maxLiveTerminals`; and it has
had no output/input/lifecycle change for at least `idleSeconds`. Visible
terminals are never touched.

Before killing, cmux sends `SIGTERM` to the agent's process group (scoped to
that workspace + surface), swaps in a lightweight placeholder, and on return
runs the agent's native resume command with the saved session ID. The
placeholder also shows a Resume button as a manual fallback.

**Implication for an agent driving cmux:** do not assume a background agent
surface's process is alive. `read-screen` to check; if hibernated, the
placeholder shows a Resume button (the human clicks it, or cmux auto-resumes
on tab focus). Make your launch commands re-runnable. The hooks save the
session ID and resume it, so a re-run continues the session rather than
starting fresh.

Disable automatic resume on relaunch if you want restored panes to stay idle
until manually resumed:

```json
{ "terminal": { "autoResumeAgentSessions": false } }
```

## Custom surface resume commands

Attach a resume command to the current terminal surface:

```bash
cmux surface resume set --shell <command>
```

Public CLI and socket-created commands are kept for inspection/manual restore
by default. To auto-run one on restore, approve the prompt or change the
signed command prefix in **Settings > Terminal > Resume Commands**. Approvals
are prefix-based, signed by cmux, and bind the working directory + exact env
values. A process can propose a command but cannot make it sticky without the
human choosing Auto-Restore or Ask Each Time.