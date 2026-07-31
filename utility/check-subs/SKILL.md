---
name: check-subs
description: |
  Probes 4 AI provider subscriptions (OpenRouter, opencode-go Go, MiniMax, Google
  AI Pro) and reports liveness and remaining quota per usage window. Writes a
  state file that any downstream consumer can read to make routing decisions.
  Use when an agent is about to dispatch a task to a subscription-based model,
  after a 429/2056/quota-exhausted response, when the user asks for current
  subscription state, or before opening a long working session.
invocation: auto
layer: utility
language: en-US
metadata:
  version: "1.0.0"
---

# check-subs — subscription liveness + quota probe

A self-triggering utility that gives any harness awareness of its subscription
state. Runs on demand (no background daemon). The user invokes it manually when
they want to inspect state; the agent invokes it before dispatching to a
subscription-based worker, and after a rate-limit error from one.

## WHEN (self-trigger)

- An agent is about to dispatch a task to a model on a subscription and wants
  to know whether that sub is currently alive and how much budget remains.
- A dispatch returned `429`, `2056`, `quota_exceeded`, or `Resource exhausted`
  and the agent needs to update the local state with the reset timestamp.
- The user opens a session and asks "what subs are live right now?" or "is
  opencode-go Go still good?".
- A long working session is starting and the agent wants a baseline before
  burning quota.
- Periodic: at session start, every 30+ minutes during heavy work, and at
  session end.

## WHAT IT DOES

Calls each subscription's quota endpoint (where one exists) and a liveness probe
(where it doesn't), aggregates the results, and writes a single JSON state file
that any process can read. Output is plain JSON, also pretty-printed to stdout
in `--human` mode.

### The 4 providers

| Provider | Mechanism | Output |
|---|---|---|
| OpenRouter | `GET /api/v1/auth/key` (Bearer) | `usage`, `usage_monthly`, `limit_remaining` |
| opencode-go Go | `GET /workspace/{id}/go` (session cookie, HTML scrape) | `5h`, `weekly`, `monthly` windows with `consumedPercent` + `resetEtaMs` |
| MiniMax | `GET /v1/token_plan/remains` (Bearer) | `5h` + `weekly` windows with `consumedPercent` + `resetEtaMs` |
| Google AI Pro | liveness probe via the `agy` CLI (cheapest model, 1-token prompt) | liveness only (v1); full quota in v1.1 via OAuth |

### Unified threshold scheme (per window, not per provider)

Thresholds apply **uniformly across all providers** for the same window name.
So `5h` window has the same warn/danger for OG, Minimax, and AGY; `weekly`
has the same warn/danger for OG and Minimax; etc.

| Window | warn | danger | Rationale |
|---|---|---|---|
| `5h` | 70% | 85% | Fast-reset window; warn earlier. |
| `weekly` | 75% | 90% | Slower reset; tighten slightly. |
| `monthly` | 80% | 95% | Slowest reset; only flag near exhaustion. |

Override per window via the config file.

## HOW TO INVOKE

```bash
# Probe all 4 providers, write state, print summary
check-subs probe

# Probe a single provider
check-subs probe openrouter
check-subs probe opencode-go
check-subs probe minimax
check-subs probe agy

# Read the current state (no probe — just shows the cached file)
check-subs status

# After a 429 / 2056 / quota-exhausted, record the reset
check-subs record <provider> <window> <consumedPercent> <resetEtaSeconds>

# Pretty-print the state to stdout in human form
check-subs status --human
```

The script lives at `scripts/check-subs.sh` in this skill. Deploy the skill
under the harness's skill-discovery path (typically `~/.agents/skills/check-subs/`
or equivalent) and add `scripts/` to PATH, OR invoke by absolute path.

## CONFIGURATION

Config is read from `$XDG_CONFIG_HOME/check-subs/config.json` (default
`~/.config/check-subs/config.json`). Schema is in `references/config.md`. Env
vars override file values. The skill auto-detects existing auth files in
common harness-specific locations as a fallback (read-only — never writes
back).

Minimal config to start:

```json
{
  "openrouter": { "apiKey": "sk-or-v1-..." },
  "opencode-go": { "workspaceId": "...", "authCookie": "auth=..." },
  "minimax":    { "apiKey": "sk-cp-..." }
}
```

`agy` needs no config — it reads its own auth.

## STATE FILE

`$XDG_STATE_HOME/check-subs/state.json` (default
`~/.local/state/check-subs/state.json`). Schema and field reference in
`references/state.md`. World-readable so any harness can consume it. Atomic
writes (write to `.tmp`, rename). 60-min retention on the debug log; state file
is overwritten in place.

## POST-DISPATCH FEEDBACK LOOP

When a dispatch returns a rate-limit error, the agent (or the calling
wrapper) MUST invoke `check-subs record <provider> <window> <percent>
<resetEtaSec>`. This updates the state and pushes the next probe out to the
reset time, avoiding wasted cycles probing a known-dead sub.

## BOUNDARIES

- MUST read existing config without writing back to harness-specific auth
  files. Read-only fallback is fine.
- MUST NOT block on a probe longer than 15 seconds (10s request + 5s retry
  overhead). If a probe hangs, mark the provider `timeout` and move on.
- MUST write the state file atomically. Other processes may be reading it.
- MUST NOT depend on any specific harness, agent, or tool runtime. The skill
  is pure bash + `curl` + `jq`.
- MUST degrade gracefully: if a single provider fails, return the others'
  data and a per-provider status flag.
- MUST NOT include the user's API keys in any log or state output (only
  masked form: `sk-or-v1-xxx...xxx`).

## DEPLOYMENT

Source of truth: this directory under the agent-skills repo.

Deploy by symlinking or copying to wherever the target harness discovers
skills (commonly `~/.agents/skills/check-subs/`, but check the harness's
docs). After deploy, the harness can invoke the skill via its native
skill-loading mechanism; the bash entry point is also directly callable.

## REFERENCES

- `references/endpoints.md` — full endpoint table with auth + response shapes
- `references/config.md` — config schema and env-var fallbacks
- `references/state.md` — state file schema and field reference
- `references/agy-quota.md` — v1.1 plan for full AGY quota via OAuth
- `scripts/` — executable entry points and per-provider probe implementations
- `examples/usage.md` — concrete invocation examples
