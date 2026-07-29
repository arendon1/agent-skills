# Agent launchers — wiring `agy` into specific harnesses

This reference covers the **harness-specific** parts of driving
`agy`: how each harness shells out, where session state lives, and
how to wire `agy` as a worker / third-opinion reviewer in each
harness's idiom. The `SKILL.md` body stays agnostic; this file is
the adapter's cheat sheet.

The `skill-forge` audit reads `SKILL.md` only — it does not scan
this file. Harness names are named directly here because that's
what these integrations do.

## The pattern (universal)

Regardless of harness, the integration is the same shape:

1. A subagent / worker lane / peer session is launched with `agy -p
   "..." --model <name> --print-timeout 5m` (or `agy -i` for
   interactive).
2. The harness captures stdout; for `--output-format json` it parses
   the envelope to read `response` and `conversation_id`.
3. The harness records the result + the `conversation_id` so the run
   can be resumed (`agy --conversation <id>`).

Where harnesses diverge: the wrapper that owns steps 1–3, the
isolation model, the resume semantics, and the way they capture
output (sync vs streamed vs PTY).

## Pi

Pi's `Agent` tool dispatches subagents in isolated git worktrees. To
use `agy` as a Pi subagent's worker backend, the subagent prompt
shells out to `agy -p` (or, for the long-running/JSON envelope path,
to `agy -p ... --output-format json --print-timeout N`).

Common shapes:

```bash
# One-shot review (subagent inside Pi)
agy -p "Review the diff in $DIFF_FILE. Output: BLOCKING, NON-BLOCKING, FOLLOW-UPS." \
    --model "gemini-3.1-pro-high" \
    --add-dir "$REPO" \
    --print-timeout 5m

# Structured output for downstream parsing (parse the JSON envelope)
agy -p "Implement $TASK" \
    --model "gemini-3.6-flash-high" \
    --dangerously-skip-permissions \
    --output-format json \
    --print-timeout 30m

# Third-opinion against a Pi-written plan (Claude path)
agy -p "Read $PLAN. Output hidden assumptions, failure modes, missing ACs." \
    --model "claude-sonnet-4-6" \
    --add-dir "$REPO" \
    --print-timeout 5m
```

Pi-side considerations:

- Pi's subagent isolation already provides cwd + a fresh worktree; if
  the subagent needs access to a second root (e.g. a shared `specs/`
  directory), pass it via `--add-dir`.
- For long runs, pass `--print-timeout 30m` (or whatever the task
  needs) and `--dangerously-skip-permissions`; the subagent wrapper
  should NOT kill the process prematurely.
- For JSON envelope parsing, the subagent must parse stdout as a
  single JSON object and read `.response` (not treat stdout as prose).
- Conversation resume: capture `conversation_id` from the envelope,
  pass to the next subagent as `--conversation <id>` if the task
  needs a multi-turn flow.

Pi's own skill convention is for skills to live in
`~/.pi/agent/skills/<name>/` (symlinked from
`~/.agents/skills/<name>/`). The `use-agy` skill follows that
convention.

## Hermes

Hermes is a coding agent at `~/.hermes/hermes-agent/`. It supports
`agy` as an **optional skill** (see
`~/.hermes/hermes-agent/optional-skills/autonomous-ai-agents/antigravity-cli/SKILL.md`).
Hermes's `terminal` tool is the wrapper for `agy` invocations.

The optional skill's documented patterns (v0.2.0 — note: it predates
the 1.1.8 JSON envelope feature; the canonical doc for current
`agy` is this skill):

```bash
# One-shot review
terminal(command="agy -p 'Review this diff for bugs and security issues' --model 'gemini-3.1-pro-high'", workdir="/path/to/repo", timeout=300)

# Long / bounded run (background + notify on complete)
terminal(command="agy -p '...' --dangerously-skip-permissions --print-timeout 30m", workdir="/path/to/repo", background=true, notify_on_complete=true)
# then: process(action="poll"/"log"/"wait", session_id=<id>)

# Interactive (PTY + tmux)
terminal(command="agy -i", workdir="/path/to/repo", pty=true, tmux=true)
```

Hermes-side considerations:

- Hermes's `kanban-worker-lanes` for external CLIs (including `agy`)
  are described as "not yet a paved path" in the Hermes docs — `agy`
  is a worker execution backend, not a first-class kanban primitive.
  Route work through the normal task graph and let the assigned
  worker choose `agy` as its method.
- Hermes's `auxiliary` slots (`title_generation`, `vision`,
  `compression`, `web_extract`, `skills_hub`, `mcp`, etc.) do not
  directly invoke `agy` — those are model-routing slots resolved
  through Hermes's own provider chain. `agy` shows up in Hermes as a
  terminal-launched tool, not as an auxiliary-slot provider.

## OpenCode

OpenCode supports `agy` via the standard shell-out path. The typical
integration is in `~/.config/opencode/agents/` or in a custom
`opencode.json` provider entry that points at `agy -p` for
non-interactive runs.

OpenCode-side considerations:

- OpenCode's provider config (`~/.config/opencode/opencode.json`)
  accepts custom `provider` entries; for `agy` to appear as a
  selectable model in OpenCode, the provider would need to wrap
  `agy -p --output-format json` and surface the `.response` field as
  the model output. This is non-trivial — most users just call `agy
  -p` from a shell command in their OpenCode workflow, not as a
  model provider.
- For background runs, OpenCode's `run_async` will tail `agy -p`'s
  stdout; pair with `--print-timeout 30m` so the wrapper doesn't
  kill the run.

## Claude Code

Claude Code and `agy` overlap heavily (both are coding-agent CLIs,
both can run a single prompt non-interactively). The main reason to
use `agy` from inside Claude Code is the **cost angle**: when a task
needs a Gemini-family cross-check, `agy -p` with
`gemini-3.1-pro-high` is free under AI Pro, whereas Claude Code
itself bills the same model through its own provider.

```bash
# From a Bash tool in Claude Code: get a Gemini cross-check
agy -p "Review the diff in $DIFF. Output only BLOCKING issues." \
    --model "gemini-3.1-pro-high" \
    --add-dir "$REPO" \
    --print-timeout 5m
```

Claude Code-side considerations:

- Claude Code's `--print` is its own non-interactive mode; the
  harness already has its own envelope, so `agy -p --output-format
  text` (default) is the right pairing — do not nest JSON envelopes.
- For Claude-family work, `agy -p` with `claude-sonnet-4-6` is the
  same model Claude Code is already calling; the only saving is
  routing the bill to Google. Not usually worth it.

## Codex

Codex (OpenAI's coding-agent CLI) overlaps with `agy` similarly to
Claude Code. Reach for `agy` from a Codex session for:

- A Gemini cross-check (cost: free under AI Pro).
- A Claude second opinion without burning your Anthropic budget.

```bash
# From Codex: cross-check the current diff with Gemini
agy -p "Audit this diff for security issues. Cite file:line." \
    --model "gemini-3.1-pro-high" \
    --add-dir "$REPO" \
    --print-timeout 5m
```

Codex-side considerations:

- Codex's own `--output-format json` is incompatible with `agy`'s;
  pick one harness's envelope per call, not both.

## Cursor

Cursor's CLI hooks (when present) accept arbitrary shell commands.
Use the same `agy -p` patterns; the wrapper handles stdout capture.

Cursor-side considerations:

- Cursor's `terminal` and `command` tools already capture stdout;
  pass `--output-format text` (default) and let Cursor parse the
  prose. For machine-readable flows, write the envelope to a file
  and read it back: `agy -p ... --output-format json > /tmp/r.json`.

## GitHub Copilot CLI

Copilot's CLI shells out the same way. Use `agy -p` for the
cost-saver use case (Gemini free, Claude via Google bill).

Copilot-side considerations:

- Copilot's own `--output-format` and `agy`'s may conflict; pass
  one or the other, not both.

## Kiro

Kiro (AWS's coding-agent CLI) is a more recent entry; the
integration is the standard shell-out shape. `agy` is the
free-Gemini path; reach for it when a Kiro session needs a Gemini
cross-check on a budget.

## Generic shell pattern (any harness)

If the harness has a `terminal` / `Bash` / `shell` tool, the
universal `agy` call is:

```bash
# Synchronous, text output
agy -p "<prompt>" --model "<exact display string>" \
    --add-dir <repo> --print-timeout 5m

# Synchronous, JSON envelope (for parsing)
agy -p "<prompt>" --model "<exact display string>" \
    --add-dir <repo> --print-timeout 5m --output-format json

# Background, long-running
agy -p "<prompt>" --model "<exact display string>" \
    --add-dir <repo> --dangerously-skip-permissions --print-timeout 30m &
LOG=$(ls -t ~/.gemini/antigravity-cli/log/cli-*.log | head -1)
tail -f "$LOG"   # until you see the run complete
```

The harness adapter chooses between the three shapes based on
whether it needs prose, structured output, or background tracking.

## Cost-aware selection (universal)

When the host harness supports multiple model providers (Pi's
`Agent` tool, Hermes's `provider_routing`, OpenCode's
`opencode.json`, etc.), the policy is:

| Task | Cheapest path | Reason |
|------|---------------|--------|
| Gemini-family work (review, refactor, code gen) | `agy -p --model gemini-3.1-pro-high` | Free under AI Pro |
| Claude-family work (without an Anthropic key) | `agy -p --model claude-sonnet-4-6` | Avoids needing an API key |
| Open-weight work (gpt-oss, etc.) | `agy -p --model gpt-oss-120b-medium` | Free-tier; avoids OR rate limits |
| Non-agy-supported model (Kimi K3, GLM 5.2, DeepSeek V4 Pro, MiniMax M3) | Host harness's native model routing | `agy` does not ship these |
| Heavy orchestration (task graph, retries, cost rollups) | Host harness dispatcher; let workers pick `agy` | `agy` is a worker, not an orchestrator |

## When to prefer the host harness directly (instead of agy)

- The work is already running on a non-Gemini model that the user
  prefers. No reason to detour through `agy` for that.
- The work needs multi-turn conversation with the user's existing
  session, not a fresh `agy` conversation. Pass `--conversation
  <id>` only if the user explicitly wants the same `agy` thread
  resumed.
- The work is a tight inner loop where the `agy -p` round-trip
  latency (~1s for `gemini-3.6-flash-low` on a one-token response)
  would dominate. Stay on the host's direct path.

## See also

- `SKILL.md` — mental model, delegation patterns, pitfalls, verification
- `commands.md` — quick reference tables
- `workflows.md` — worked sequences (one-shot, batch, second-opinion, log triage)
- `topology.md` — paths, settings, auth, models, JSON envelope schema
