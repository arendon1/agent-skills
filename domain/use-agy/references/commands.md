# Commands — quick reference

Compact command tables for `agy`. For delegation patterns and output
caveats see the main `SKILL.md`; for worked sequences see
`workflows.md`.

## Global options (run-mode)

| Option | Effect |
|--------|--------|
| `--add-dir <path>` | Add a workspace root (repeatable; default `[]`) |
| `--agent <name>` | Agent for the current CLI session |
| `-c`, `--continue` | Resume the most recent conversation |
| `--conversation <id>` | Resume a specific conversation |
| `--dangerously-skip-permissions` | Auto-approve all tool permission requests |
| `--effort low\|medium\|high` | Reasoning effort for the session |
| `-i`, `--prompt-interactive` | Interactive REPL with initial prompt |
| `--json-schema <schema>` | JSON schema string or path for structured output (stream-json final result) |
| `--log-file <path>` | Override the CLI log file path |
| `--mode accept-edits\|plan` | Agent execution mode |
| `--model <name>` | Model for the current session (exact display string) |
| `--new-project` | Create a new project for this session |
| `--output-format text\|json\|stream-json` | `-p` output format (default `text`) |
| `-p`, `--print`, `--prompt` | Non-interactive single prompt |
| `--print-timeout <dur>` | Bound `-p` run (default `5m0s`) |
| `--project <id>` | Use a specific project ID |
| `--prompt-interactive <text>` | Interactive REPL with initial prompt |
| `--sandbox` | Run in a sandbox with terminal restrictions |

## Wrapper subcommands

```bash
agy --version                    # safe non-interactive version check
agy help                         # wrapper surface (NOT slash commands)
agy changelog                    # release notes
agy install [--dir PATH] [--skip-aliases] [--skip-path]
agy update                       # self-update (polls every 15m otherwise)
agy models                       # installed models with display strings
agy agents                       # available agents (may be empty)
agy plugin <subcommand>          # see Plugin subcommands below
```

## Plugin subcommands (`agy plugin --help`)

```bash
agy plugin list                  # list imported plugins
agy plugin import [source]       # import plugins from gemini or claude
agy plugin install <target>      # install (supports plugin@marketplace)
agy plugin uninstall <name>
agy plugin enable <name>
agy plugin disable <name>
agy plugin validate [path]
agy plugin link <mp> <target>    # generate link to a marketplace
agy plugin help
```

## Install subcommand (`agy install --help`)

```bash
agy install [--dir <PATH>] [--skip-aliases] [--skip-path]
```

`--dir` chooses where to wire PATH; `--skip-aliases` keeps the shell
profile untouched; `--skip-path` skips the PATH append.

## One-shot pattern (most common)

```bash
agy -p "<prompt>" \
    --model "<exact display string from agy models>" \
    --add-dir <repo> \
    --print-timeout 5m
```

Bindings worth remembering:

- `--model` value must match `agy models` output **exactly** (case +
  dashes + tier suffix). Typos fail silently with a "model not found"
  error.
- `--print-timeout` accepts Go duration syntax: `30s`, `5m`, `1h30m`,
  `20m`.
- `--output-format json` for `-p` returns a single-line result envelope
  with `conversation_id`, `status`, `response`, `duration_seconds`,
  `num_turns`, and `usage` (input/output/thinking/cache_read/total
  tokens). The model reply is in `.response`, not on stdout directly.
  Parse it as JSON; this is the scripted-pipeline shape.
- `--output-format stream-json` emits newline-delimited JSON events
  (`message_start`, `content_block_delta`, `message_stop`, ...) for
  line-buffered consumers that want progress as the agent thinks. Pair
  with `--json-schema <schema-or-path>` to enforce structure on the
  final result.
- `--add-dir` is repeatable; the launch cwd is always included.

## Background / long-running pattern

```bash
agy -p "<prompt>" \
    --model "gemini-3.6-flash-high" \
    --dangerously-skip-permissions \
    --print-timeout 30m
```

Verification: tail the latest log file, **don't** trust exit code alone.

```bash
LOG=$(ls -t ~/.gemini/antigravity-cli/log/cli-*.log | head -1)
tail -f "$LOG"
```

## Interactive pattern

```bash
# Start fresh
agy -i "Start by reading README.md and summarizing the project"

# Resume most recent
agy -c

# Resume specific
agy --conversation <id>
```

For agent-driven interactive control, run `agy -i` under tmux / herdr /
cmux and drive it with the host's send-keys API. See `SKILL.md` →
"Interactive multi-turn".

## Permission modes

| Mode | Behavior |
|------|----------|
| `request-review` | Ask before each tool call (default) |
| `always-proceed` | Auto-approve everything |
| `strict` | Block anything not explicitly allowed |
| `proceed-in-sandbox` | Auto-approve inside the sandbox only |

Set in `~/.gemini/antigravity-cli/settings.json` under
`permissions.allow` / `toolPermission`. Per-session overrides:
`--sandbox`, `--dangerously-skip-permissions`.

## Sandbox setting

`enableTerminalSandbox` (boolean, default `false`) in `settings.json`.
Launch override: `--sandbox`. Sandbox = terminal restrictions; it does
**not** auto-approve tool calls (combine with `--dangerously-skip-permissions`
only if you mean both).

## Settings file locations

| File | Purpose |
|------|---------|
| `~/.gemini/antigravity-cli/settings.json` | User persistent settings (created on first write) |
| `~/.gemini/antigravity-cli/keybindings.json` | Keybindings (malformed JSON falls back to defaults) |
| `~/.gemini/config/config.json` | Shared config (CLI permissions source when `settings.json` is absent) |

## Log file layout

- Active log: `~/.gemini/antigravity-cli/log/cli-YYYYMMDD_HHMMSS.log`
- Convenience symlink: `~/.gemini/antigravity-cli/cli.log` → active file
- Rotate by mtime, not filename pattern; the timestamp is the launch
  time, not the rotation time.
- Levels: `I` info, `W` warn, `E` error. Failures start with `E`.

## Useful one-liners

```bash
# Latest log
LOG=$(ls -t ~/.gemini/antigravity-cli/log/cli-*.log | head -1)

# Auth state (look for "Auth succeeded" vs "You are not logged into Antigravity")
grep -E "Auth succeeded|not logged into" "$LOG" | tail -5

# Last 50 lines
tail -50 "$LOG"

# Errors only
grep "^E" "$LOG" | tail -20

# Smoke test (text)
agy -p "Reply with: pong" --model gemini-3.5-flash-low --print-timeout 1m

# Smoke test (JSON envelope — capture conversation_id for resume)
agy -p "Reply with: pong" --model gemini-3.5-flash-low \
    --output-format json --print-timeout 1m \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['conversation_id'], d['response'].strip())"

# List installed models
agy models

# List plugins (empty is valid)
agy plugin list
```

## When not to reach for agy

- The work needs a model `agy` doesn't ship (Kimi K3, GLM 5.2, DeepSeek
  V4 Pro, MiniMax M3, etc.). Use the host harness's native routing.
- The work needs an orchestrator (task graph, retries, cost rollups).
  `agy` is a worker; route via the host's dispatcher.
- The user has no Google AI Pro subscription AND wants to stay free —
  then `agy` with Claude/`gpt-oss` is not free, and Gemini via OpenRouter
  with the user's own key may be cheaper. Check before recommending.

## See also

- `SKILL.md` — mental model, delegation patterns, model table,
  pitfalls, verification
- `workflows.md` — worked sequences for one-shot review, parallel
  batch, second-opinion cross-check, log triage
