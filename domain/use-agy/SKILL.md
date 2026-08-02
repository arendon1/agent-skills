---
name: use-agy
description: |
  Use the Antigravity CLI (`agy`) as a worker or third-opinion reviewer from any
  agent harness. `agy` is Google's agentic coding-agent backend (same family as
  `codex` / `claude-code`); auth is OS-keyring + browser Google sign-in, so its
  **Gemini models ride on Google AI Pro at zero marginal token cost**. Reach
  for `agy` for a cheap Gemini answer, a Claude-family second opinion on
  another agent's plan or diff, or a sandboxed multi-turn coding session
  outside the host's model menu. `agy` is a worker, not an orchestrator —
  route work through the normal task graph.
  Use when running a one-shot `agy -p` review or change, launching an
  interactive `agy -i` session, fanning a parallel batch across git worktrees
  with one `agy -p` each, picking a Gemini model on a Google AI Pro budget,
  asking for a Claude Sonnet/Opus second opinion on a plan or diff, inspecting
  `~/.gemini/antigravity-cli/`, or debugging auth/sandbox/permission state.
invocation: auto
layer: domain
provides: [agy-worker]
language: en-US
metadata:
  version: "1.1.0"
---

# use-agy

Domain capability for the **AGY CLI** (`agy` is the binary name).
`agy` is a single-binary agentic coding agent from Google — same shape as
`codex` / `claude-code`, but with two properties that matter here:

1. **Auth is Google sign-in, not an API key.** Credentials live in the OS
   keyring (or browser-based OAuth on a fresh machine). No `OPENAI_API_KEY`,
   no `ANTHROPIC_API_KEY`, no env to set.
2. **Gemini models ride on Google AI Pro.** When the user has Google AI Pro,
   Gemini-class work via `agy` is effectively **free** — the marginal cost
   is the subscription, not per-token. Claude and `gpt-oss` paths still
   incur whatever Google charges for those tiers; check before reaching for
   them.

That cost profile is the main reason this skill exists: `agy` is the
cheapest path to a Gemini-quality answer, and a clean way to get a
Claude-family second opinion without leaving the host harness.

**Canonical source:** `agy --help`, `agy help`, `agy models`, and the
latest `~/.gemini/antigravity-cli/log/cli-*.log` are authoritative for the
installed version. `agy changelog` and `agy update` track upstream.

## Mental model

`agy` has two layers — keep them distinct or the commands will look wrong:

1. **Shell wrapper commands** — `agy help`, `agy install`, `agy plugin`,
   `agy update`, `agy changelog`, `agy models`, `agy agents`. Run these from
   any agent shell.
2. **In-session slash commands** — `/config`, `/permissions`, `/skills`,
   `/agents`, `/resume`, `/model`, etc. These only exist inside a running
   `agy` TUI / REPL session, not on the shell wrapper.

`agy help` shows the wrapper surface, NOT the slash commands. To see slash
commands, start `agy` interactively or read the docs page.

A running `agy` is one **project** with an optional `--conversation <id>`
for resume. `--continue` / `-c` resumes the most recent conversation.
Conversations persist under `~/.gemini/antigravity-cli/conversations/`.

## Prerequisites

- The `agy` binary on `PATH`. Verify with `command -v agy && agy --version`
  (currently `1.1.x`).
- An authenticated Google session in the OS keyring (or browser OAuth on a
  fresh machine). No API key needed.
- **No env vars** are required by `agy` itself. If the host harness has its
  own `GOOGLE_API_KEY` or `GEMINI_API_KEY` set for a different tool,
  `agy` ignores it — auth is keyring-based.

If `agy --version` works but every call fails with auth errors, the
keyring is empty — see [Authentication](#authentication) below.

## When to prefer `agy` (and when not to)

| Task | Cheapest path | Why |
|------|---------------|-----|
| Gemini-quality code review / refactor / write | **`agy -p` with a Gemini model** | Free under Google AI Pro |
| Vision / image-input reads (OCR, infographics, screenshots, scanned PDFs) | **`agy -p` with a Gemini model** | Gemini is multimodal by default — free under AI Pro. See **Workflow J** for the 3 gotchas (relative path in prompt, `--dangerously-skip-permissions`, strip boilerplate). For corpus-scale ingestion prefer host subagents on `minimax/MiniMax-M3`. |
| Claude Sonnet/Opus second opinion on a plan or diff | **`agy -p` with `claude-sonnet-4-6` / `claude-opus-4-6-thinking`** | Avoids loading Claude via another vendor |
| Multi-turn coding session the user wants to drive interactively | **`agy -i` under PTY + tmux / herdr / cmux** | Native TUI with slash commands |
| Parallel batch of independent tasks | **One git worktree per task, `agy -p` in each** | Same shape as the `codex` skill's worktree fan-out |
| Reach a model `agy` does not offer (Kimi K3, GLM 5.2, DeepSeek V4 Pro, MiniMax M3, etc.) | **Use the host harness's native model routing** | `agy` is Gemini/Claude/gpt-oss only — see [Model selection](#model-selection) |
| Heavy orchestration (task graph, retries, cost reporting) | **Host harness dispatcher; let workers pick `agy`** | `agy` is a worker, not an orchestrator |

## Delegation patterns

`agy` is a coding-agent backend; the same delegation shapes as `codex` /
`claude-code` apply. Pick the pattern that matches the work, not the
harness.

### One-shot non-interactive (preferred for reviews and scripted prompts)

```
agy -p "Review this diff for bugs and security issues" \
    --model "gemini-3.1-pro-high" \
    --add-dir <repo> \
    --print-timeout 5m
```

`-p` (alias `--print`, `--prompt`) runs the prompt and exits. Pick the
engine with `--model` (use `agy models` for the exact display strings —
**the display names are exact, not aliases**). Add extra context roots with
repeatable `--add-dir`. Bound long runs with `--print-timeout` (Go duration
syntax with unit: `60s`, `5m`, `30m` — a bare integer like `60` is rejected
with `time: missing unit in duration`. Default
`5m`); see [Output and bounding](#output-and-bounding) below.

This is the right shape for a second-opinion review of another agent's
plan or diff, a code-quality audit, or a one-shot script-style invocation.

### Long-running / bounded runs (tests, builds, multi-file changes)

Background it from the host shell, same pattern as `codex` /
`claude-code`:

```
agy -p "Implement TASK.md and run the test suite" \
    --model "gemini-3.6-flash-high" \
    --dangerously-skip-permissions \
    --print-timeout 30m
# Background; poll the log file at ~/.gemini/antigravity-cli/log/cli-*.log
```

`--dangerously-skip-permissions` auto-approves tool calls. Pair it with
`--print-timeout` so the run has headroom. Always verify completion by
reading the **latest** `cli-*.log`, not the launch command's exit code —
`agy -p` exits 0 even on partial completion.

### Interactive multi-turn (PTY + tmux / herdr / cmux)

For a conversational session, launch `agy -i` (or bare `agy`) under PTY
with a multiplexer so the host can `capture-pane` / `send-keys` against
it. Resume later with `--continue` / `-c` or a specific
`--conversation <id>`.

In a tmux pane:

```
# Start fresh
tmux send-keys -t agy 'cd ~/projects/myapp && agy -i' Enter

# Resume the most recent
tmux send-keys -t agy 'agy -c' Enter

# Resume a specific conversation
tmux send-keys -t agy 'agy --conversation <id>' Enter
```

In a herdr pane, the same pattern with `herdr pane run` (see the
`use-herdr` skill, Workflow D). In cmux, use `cmux send --surface <s>
"agy -i\n"` (see the `use-cmux` skill, Workflow D).

### Parallel batch (worktree fan-out)

For N independent tasks (e.g. batch issue triage, parallel file rewrites),
create one git worktree per task and launch an independent `agy -p` in
each. Bound concurrency to what the machine and your review capacity can
absorb — `agy` is heavier than `codex`, so default to 2–3 in parallel.

```bash
# For each task id in $TASKS:
git worktree add ../wt-$TASK -b fix/$TASK
(cd ../wt-$TASK && agy -p "$(cat ../prompt-$TASK.txt)" \
   --model "gemini-3.6-flash-medium" \
   --dangerously-skip-permissions \
   --print-timeout 15m > ../out-$TASK.txt 2>&1) &
```

Collect `out-*.txt` results; per-worktree success = clean diff + exit 0.
Same shape as the `codex` skill's batch issue fixing.

### Second-opinion review (the highest-leverage use)

Cross-check another agent's plan or diff against a different model family
without leaving the host session:

```bash
# Plan review
git -C ~/projects/myapp diff main..HEAD > /tmp/diff.txt
agy -p "Review the diff in /tmp/diff.txt. Output: (1) blocking issues,
(2) non-blocking issues, (3) suggested follow-ups. Be terse." \
   --model "claude-sonnet-4-6" \
   --add-dir ~/projects/myapp \
   --print-timeout 5m
```

Or against Gemini itself for a different-perspective check:

```bash
agy -p "Same diff. Output only blocking issues." \
   --model "gemini-3.1-pro-high" \
   --add-dir ~/projects/myapp \
   --print-timeout 5m
```

Capture the output verbatim into the plan folder's `RESEARCH.md` or
`LESSONS.md` so the cross-check is part of the audit trail.

## Output and bounding

`agy -p` has three output modes. Pick deliberately — the default is the
wrong choice for scripted pipelines.

- **`--output-format text` (default).** Plain prose to stdout. The agent's
  reply is natural language; parse stdout directly. This is the same shape
  as `claude-code` `--print` text mode.
- **`--output-format json`.** Final-result envelope to stdout (single
  line, parseable as JSON). Schema:
  ```
  {
    "conversation_id": "<uuid>",   // resume with --conversation <id>
    "status": "SUCCESS",            // or failure
    "response": "<agent reply>",   // the actual answer, may be multi-line
    "duration_seconds": 1.47,
    "num_turns": 1,
    "usage": {
      "input_tokens": 17558,
      "output_tokens": 67,
      "thinking_tokens": 60,
      "cache_read_tokens": 0,
      "total_tokens": 17625
    }
  }
  ```
  This IS the `session_id` / cost / turn count envelope the v0.2.0
  reference claimed was missing. Verified on `agy 1.1.8`. Use it for any
  scripted pipeline that needs to capture `conversation_id` (for
  `--continue` / `--conversation`) or per-run cost telemetry.
- **`--output-format stream-json`.** Newline-delimited JSON events
  (`message_start`, `content_block_delta`, `message_stop`, etc.) for
  line-buffered consumers that want progress as the agent thinks. Pair
  with `--json-schema <schema-or-path>` to enforce structure on the
  final result.

The model reply is in `response` (not on stdout) when using `json` —
don't parse stdout as prose, parse the JSON and read `.response`.

**No `--max-turns` on `agy`.** Bound print runs with `--print-timeout`
(default `5m0s`). Raise it for long tasks: `--print-timeout 20m`. Pair
with the host harness's outer timeout so the wrapper doesn't cut the
run short. `agy -p` exits 0 even on partial completion — verify with the
result envelope's `status` field, not the process exit code.

## Model selection

`agy models` (run it for the current list) shows the installed model set.
As of writing:

| Display name | Tier | Cost path |
|--------------|------|-----------|
| `gemini-3.6-flash-high` | fast/cheap | **Free under Google AI Pro** |
| `gemini-3.6-flash-medium` | fast/cheap | **Free under Google AI Pro** |
| `gemini-3.6-flash-low` | fast/cheap | **Free under Google AI Pro** |
| `gemini-3.5-flash-high` | fast/cheap | **Free under Google AI Pro** |
| `gemini-3.5-flash-medium` | fast/cheap | **Free under Google AI Pro** |
| `gemini-3.5-flash-low` | fast/cheap | **Free under Google AI Pro** |
| `gemini-3.1-pro-high` | strong/balanced | **Free under Google AI Pro** |
| `gemini-3.1-pro-low` | strong/balanced | **Free under Google AI Pro** |
| `claude-sonnet-4-6` | premium | Billed per Google terms (not subscription-free) |
| `claude-opus-4-6-thinking` | premium | Billed per Google terms (not subscription-free) |
| `gpt-oss-120b-medium` | open-weight | Billed per Google terms |

**Rule of thumb:** for Gemini work, pick `agy` over the host harness's
OpenRouter path — same model family, zero marginal cost under AI Pro. For
Claude work, pick `agy` only if the alternative is *no* Claude access (no
OpenRouter Claude key configured) or if the user wants to keep Claude
spend inside the Google bill.

`agy` does **not** ship the user's preferred models (Kimi K3, GLM 5.2,
DeepSeek V4 Pro, MiniMax M3, etc.). For those, route through the host
harness's native model routing — `agy` is the wrong tool.

Reasoning effort: `--effort low|medium|high` controls thinking depth for
the current session. Default is medium; raise to `high` for hard reviews.

## Context roots

`agy` reads files from the **launch directory** and any `--add-dir`
roots. Add context explicitly:

```
agy -p "..." --add-dir ~/projects/myapp --add-dir ~/shared/specs
```

`--add-dir` is repeatable. Files outside `--add-dir` and the cwd are not
visible to the agent by default — same access model as `claude-code`.

## Sandbox and permissions

Three layers; pick the strictest that the task allows.

**Launch-time flags:**
- `--sandbox` — run in a sandboxed shell with terminal restrictions.
- `--dangerously-skip-permissions` — auto-approve every tool call (CI /
  background runs).

**Persistent settings (`~/.gemini/antigravity-cli/settings.json`):**
- `enableTerminalSandbox` (boolean, default `false`)
- `allowNonWorkspaceAccess`
- `permissions.allow` (allow-list of tool actions)
- `trustedWorkspaces`

**Permission modes:**
- `request-review` — ask before each tool call (default for new sessions)
- `always-proceed` — auto-approve
- `strict` — block anything not explicitly allowed
- `proceed-in-sandbox` — auto-approve inside the sandbox only

Launch flags supersede persistent settings for the current session. Don't
confuse them.

## Authentication

- The CLI tries the OS secure keyring first.
- With no saved session, it falls back to browser-based Google sign-in.
- Locally it opens the default browser; over SSH it prints an authorization
  URL and expects the auth code pasted back.
- `/logout` removes saved credentials.
- WSL: token storage is file-based; auth issues are usually local-file /
  session-state problems, not browser-only problems.

Look for the **log-error pattern** before assuming a real auth failure —
`error getting token source: You are not logged into Antigravity` (the
literal string) followed by `Print mode: silent auth succeeded` is a
**non-fatal transient** (initial cache refresh lost a race with the
keyring; silent auth recovered; the run completed normally). Ignore the
warning if the run succeeded.

If the error keeps repeating with **no** `silent auth succeeded` line
after it, or the run actually fails, the keyring is empty. Run `agy -i`
once to trigger browser OAuth, then exit; subsequent `-p` calls reuse
the keyring.

## Orchestration boundary

`agy` is a **worker execution backend or third-opinion reviewer** — an
execution detail owned by the agent/profile running a task, **NOT** a
first-class orchestration primitive.

- Do **not** put `agy` on a kanban board as its own card.
- Do **not** treat `agy` as a coordination layer.
- Route work through the normal task graph; let the assigned worker choose
  `agy` (vs `codex` / `claude-code` / direct tools) as its method.
- Reach for `agy` explicitly only when the user asks, when a worker is
  configured to wrap it, or when you want a Gemini-family cross-check
  against another agent's plan or diff.

## Core paths

- Binary / entrypoint: `~/.local/bin/agy` (or wherever `agy` resolves on `PATH`)
- App data dir: `~/.gemini/antigravity-cli/`
- Settings file: `~/.gemini/antigravity-cli/settings.json` (created on first write — absent means defaults)
- Keybindings file: `~/.gemini/antigravity-cli/keybindings.json` (created on first write)
- Logs: `~/.gemini/antigravity-cli/log/cli-YYYYMMDD_HHMMSS.log` (latest by mtime; active log symlinked at top level as `~/.gemini/antigravity-cli/cli.log`, not inside `log/`)
- Conversations: `~/.gemini/antigravity-cli/conversations/` · Brain artifacts: `~/.gemini/antigravity-cli/brain/`
- History: `~/.gemini/antigravity-cli/history.jsonl` (created on first write — absent means no history yet)
- Plugin staging: `~/.gemini/antigravity-cli/plugins/<plugin_name>/` (created on first plugin import — absent means no plugins imported yet)
- Shared config: `~/.gemini/config/config.json` (CLI permissions source when `settings.json` is absent)
- Helper binary: `~/.gemini/antigravity-cli/bin/agentapi` → thin wrapper
  to `agy agentapi`

## Quick Reference

### Wrapper commands

| Command | Purpose |
|---------|---------|
| `agy --version` | Version (safe non-interactive) |
| `agy help` | Wrapper surface (NOT slash commands) |
| `agy changelog` | Release notes |
| `agy install` | Configure PATH / shell profile |
| `agy update` | Self-update |
| `agy models` | List installed models (display strings) |
| `agy agents` | List available agents |
| `agy plugin list` | List imported plugins |

### Useful flags (run-mode)

| Flag | Effect |
|------|--------|
| `-p`, `--print`, `--prompt` | Non-interactive single prompt |
| `--model <name>` | Pick model (exact display string from `agy models`) |
| `--effort low\|medium\|high` | Reasoning effort for the session |
| `--add-dir <path>` | Repeatable context root |
| `--print-timeout <dur>` | Bound `-p` run (default `5m`) |
| `--output-format text\|json\|stream-json` | `-p` output format |
| `-i`, `--prompt-interactive` | Interactive REPL with initial prompt |
| `-c`, `--continue` | Resume most recent conversation |
| `--conversation <id>` | Resume a specific conversation |
| `--sandbox` | Sandbox shell |
| `--dangerously-skip-permissions` | Auto-approve all tool calls |
| `--mode accept-edits\|plan` | Agent execution mode |
| `--new-project` | Start a new project for this session |
| `--project <id>` | Use a specific project ID |
| `--log-file <path>` | Override log file path |
| `--json-schema <schema>` | Enforce structured output (stream-json final result) |

### Plugin subcommands (`agy plugin --help`)

`list`, `import [source]`, `install <target>`, `uninstall <name>`,
`enable <name>`, `disable <name>`, `validate [path]`, `link <mp>
<target>`, `help`. Plugins bundle skills, agents, rules, MCP servers,
and hooks; `agy plugin list` returning empty is a valid state.

### In-session slash commands

Only inside a running `agy` TUI / REPL — full list in
`references/commands.md`. Short version: `/resume` (`/switch`),
`/rewind` (`/undo`), `/rename`, `/clear`, `/fork`, `/reset`, `/new`,
`/config`, `/settings`, `/permissions`, `/model`, `/skills`, `/mcp`,
`/open`, `/usage`, `/logout`, `/agents`. Prompt helpers: `@` path
autocomplete, `esc esc` clears, `!` runs a shell command, `?` opens help.

## Pitfalls

- `agy help` shows wrapper commands, **not** interactive slash commands.
- `agy --version` is the safe non-interactive check; `agy version` is
  interactive and can fail without a real TTY.
- First place to look for failures: `~/.gemini/antigravity-cli/log/cli-*.log`
  (latest by mtime). `cli.log` is a symlink to the active file.
- Don't confuse persistent JSON settings with launch-time flags —
  flags win per-session.
- `~/.gemini/antigravity-cli/bin/agentapi` is a thin wrapper to
  `agy agentapi`; don't edit it.
- On WSL, auth issues are file-based, not browser-only.
- Workspace identity can depend on launch directory and the
  `.antigravitycli` project marker.
- `agy -p` defaults to plain text — pass `--output-format json` to get
  a result envelope (`conversation_id` / `status` / `response` / `usage`).
  The model reply is in `response`, not on stdout directly.
- **No `--max-turns`.** Bound print runs with `--print-timeout` (default `5m`, Go duration unit required: `60s` not `60`).
- `--add-dir` is the only way to grant a second workspace; files outside cwd + `--add-dir` are not visible.
- `--dangerously-skip-permissions` is **not** `--sandbox`. First auto-approves; second sandboxes. Pick the right one.
- Auto-updater polls every 15 minutes (`Last check was less than 15
  minutes ago, skipping update`); it will restart the binary under you if
  a new version lands mid-run. Run `agy update` deliberately.
- **Image gen burns a per-model quota, not RPM.** Image gen runs on `gemini-3.1-flash-image` regardless of `--model`; ~10-12 calls/~5h on AI Pro, then `QUOTA_EXHAUSTED (429)` (non-transient, agy won't retry, `--model` switch won't help). Parse `quotaResetTimeStamp` from the log; `sleep 30` between calls. Fallback to OpenRouter (`google/gemini-3.1-flash-image`, same model, pay-per-use) **requires user approval** — never switch silently to a paid path. See `references/topology.md` → **Quota exhaustion** and `references/workflows.md` → **Workflow I**.
- **Image *input* (vision) needs three things: a relative path in the prompt, `--dangerously-skip-permissions`, and a Gemini model.** `--add-dir <image>` does NOT attach the image as vision input (agent replies it sees no image); `@path` syntax times out. Without `--dangerously-skip-permissions`, headless `-p` auto-denies `read_file` on the image and can still report `status: SUCCESS` with an empty `response` — a silent failure. The JSON `response` also carries background-task boilerplate to strip. Verified `agy 1.1.9`; see `references/workflows.md` → **Workflow J**.

## Verification

Before trusting `agy` on real work, confirm the install is real and
authenticated:

1. `command -v agy && agy --version` — binary on PATH, version non-empty.
2. `agy models` — returns at least one model (proves auth or local model
   cache is alive).
3. `agy help` — wrapper surface prints without auth errors.
4. `agy plugin list` — empty list is valid; failures here are auth-shaped.
5. Read `~/.gemini/antigravity-cli/settings.json` if it exists — confirms
   persistent settings; absence means defaults.
6. Read the **latest** `~/.gemini/antigravity-cli/log/cli-*.log` (sort
   by mtime) — should show `Auth succeeded` and `initialized server
   successfully`. If the auth-error pattern repeats on every line with
   no recovery, the keyring is empty.
7. Smoke test with a cheap Gemini one-shot:
   `agy -p "Reply with: pong" --model gemini-3.5-flash-low --print-timeout 1m`.
   If it returns `pong`, auth + model resolution + `-p` round-trip are
   all good.
8. If step 7 fails with auth errors, run `agy -i` once to trigger browser
   OAuth, sign in, then `/logout` is **not** what you want — just exit.
   Re-run step 7.
9. Smoke-test the JSON envelope:
   `agy -p "Reply with: pong" --model gemini-3.5-flash-low --output-format json`
   should print a single JSON line with `conversation_id`, `status`,
   `response: "pong"`, and a `usage` block. If it does, the full
   scripted-pipeline surface is verified.

## References

| File | When to load |
|------|--------------|
| `references/commands.md` | Quick-reference command tables, all wrapper subcommands, install/update flow |
| `references/workflows.md` | Worked workflows: one-shot review, parallel batch, second-opinion, resume, log triage |
| `references/topology.md` | Deep model table, settings.json schema, permission modes, auth + quota, JSON envelope schema |
| `references/agent-launchers.md` | Harness-specific launchers (per-adapter `agy -p` shapes for each host) |

Adapted from the MIT-licensed Hermes `antigravity-cli` skill by Tony Simons
(asimons81) — `~/.hermes/hermes-agent/optional-skills/autonomous-ai-agents/antigravity-cli/SKILL.md`.
Claims verified live against `agy` 1.1.8 (model list, `--output-format json`
envelope, flag surface); the Hermes v0.2.0 "no JSON envelope" note is stale.

Authoritative external sources (run them, don't paste stale text):

- `agy --help`, `agy help`, `agy models`, `agy agents`
- `agy changelog` — release notes for the installed version
- `~/.gemini/antigravity-cli/log/cli-*.log` — runtime truth for the installed version
- `https://antigravity.google/docs/` — official docs site
