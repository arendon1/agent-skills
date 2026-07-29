# Topology — paths, settings, auth, models, schemas

Depth on the `agy` runtime. The `SKILL.md` covers the delegation
patterns; this is the reference for exact paths, settings schema,
permission modes, the JSON envelope shape, the model table with cost
annotations, and the auth/quota surface.

## Core paths

| Path | Purpose | Notes |
|------|---------|-------|
| `agy` (binary) | Entrypoint | `~/.local/bin/agy` by default; whatever `command -v agy` resolves |
| `~/.gemini/antigravity-cli/` | App data dir | Created on first launch |
| `~/.gemini/antigravity-cli/settings.json` | User persistent settings | **Not** created by default — absence means defaults are used |
| `~/.gemini/antigravity-cli/keybindings.json` | TUI keybindings | May not exist by default; malformed JSON falls back to defaults |
| `~/.gemini/antigravity-cli/log/cli-YYYYMMDD_HHMMSS.log` | Per-launch log | Latest by mtime; `cli.log` is a symlink to the active one |
| `~/.gemini/antigravity-cli/conversations/` | Saved conversation state | IDs reused by `--conversation <id>` and `--continue` |
| `~/.gemini/antigravity-cli/brain/` | Per-conversation artifacts (notes, plans, todos) | Read when resuming or auditing |
| `~/.gemini/antigravity-cli/history.jsonl` | REPL history (interactive sessions) | |
| `~/.gemini/antigravity-cli/plugins/<name>/` | Plugin staging | `agy plugin list` returning empty is a valid state |
| `~/.gemini/antigravity-cli/bin/agentapi` | Helper wrapper around `agy agentapi` | Don't edit; it's a thin shim |
| `~/.gemini/config/config.json` | Shared config (CLI permissions source when `settings.json` is absent) | Distinct from `antigravity-cli/settings.json` |

The auto-updater polls every 15 minutes — when a new version lands it
restarts the binary under you. Run `agy update` deliberately if you
need to control timing.

## Settings schema (`settings.json`)

The file is **not** present on a clean install; the log will show
`Failed to read cli settings: ... no such file or directory` and the
CLI proceeds with defaults. Create it only if you need persistent
behavior beyond defaults.

Known keys (per `agy help` + observed log behavior):

| Key | Type | Default | Effect |
|-----|------|---------|--------|
| `enableTerminalSandbox` | bool | `false` | Enable terminal sandbox globally |
| `allowNonWorkspaceAccess` | bool | `false` | Allow tool calls outside the launch cwd + `--add-dir` roots |
| `permissions.allow` | string[] | `[]` | Allow-list of tool actions; bypasses `request-review` |
| `permissions.deny` | string[] | `[]` | Explicit deny-list |
| `permissions.ask` | string[] | `[]` | Force `request-review` even when `allow` matches |
| `colorScheme` | string | (terminal default) | UI color scheme |
| `trustedWorkspaces` | string[] | `[]` | Paths to grant non-workspace access without prompt |
| `toolPermission` | string | `request-review` | Default mode: `request-review` \| `always-proceed` \| `strict` \| `proceed-in-sandbox` |
| `copyOnSelect` | bool | `true` | Auto-copy mouse text-selection in TUI altscreen mode |

**Launch flags supersede persistent settings per session.** The most
common launch overrides are `--sandbox` (sandbox the shell) and
`--dangerously-skip-permissions` (auto-approve tool calls). They are
**not** the same thing: `--sandbox` restricts the terminal, the other
bypasses tool permission prompts. Combine both only if you mean both.

Back the file up before editing:

```bash
SETTINGS=~/.gemini/antigravity-cli/settings.json
[ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d_%H%M%S)"
cat > "$SETTINGS" <<'EOF'
{
  "enableTerminalSandbox": true,
  "allowNonWorkspaceAccess": false,
  "permissions": {
    "allow": ["read_file", "list_directory", "grep_files", "web_search"]
  },
  "trustedWorkspaces": ["~/projects/myapp"]
}
EOF
python3 -m json.tool "$SETTINGS" > /dev/null && echo "OK" || echo "INVALID"
```

Settings are re-read on each launch; no explicit reload. For a running
session, restart `agy`.

## Permission modes

| Mode | Behavior |
|------|----------|
| `request-review` | Ask before each tool call (default for new sessions) |
| `always-proceed` | Auto-approve everything |
| `strict` | Block anything not explicitly allowed |
| `proceed-in-sandbox` | Auto-approve inside the sandbox only |

Set globally via `toolPermission` in `settings.json`; per-session via
`--dangerously-skip-permissions` (closest to `always-proceed`) or
`--sandbox` (enables sandbox + `proceed-in-sandbox` semantics for the
shell).

## Model table

`agy models` (run it for the installed list) shows the exact display
strings. The names are case- and dash-sensitive — typos fail with
`Model ID <x> not in local config`. Current set:

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

**`agy` does not ship the user's preferred models** (Kimi K3, GLM 5.2,
DeepSeek V4 Pro, MiniMax M3, etc.). For those, route through the host
harness's native model routing — `agy` is the wrong tool.

**Cost-optimizer rule:** for Gemini work, `agy` is the cheapest path
because the AI Pro subscription covers the marginal tokens. For
Claude work, `agy` is the right tool only if the alternative is no
Claude access (no OR Claude key) or the user wants the spend to land
on Google's bill rather than Anthropic's. For non-AI-Pro subscribers
the Gemini routes via OpenRouter (with the user's own key) may be
cheaper — check before recommending.

Reasoning effort: `--effort low|medium|high` controls thinking depth
for the current session. Default is medium; raise to `high` for hard
reviews.

## JSON output envelope (agy 1.1.8+)

`-p` supports three output formats:

### `text` (default)

Plain prose to stdout — the agent's reply is the raw output. This is
the `claude-code --print` text-mode shape.

### `json`

A single-line result envelope to stdout, parseable as JSON. Verified
on `agy 1.1.8` with `gemini-3.6-flash-low`:

```json
{
  "conversation_id": "bb39cbd7-e1f4-4fcc-8a44-39c082b3028e",
  "status": "SUCCESS",
  "response": "JSON_OK\n",
  "duration_seconds": 1.467508,
  "num_turns": 1,
  "usage": {
    "input_tokens": 18735,
    "output_tokens": 7,
    "thinking_tokens": 0,
    "cache_read_tokens": 0,
    "total_tokens": 18742
  }
}
```

Field semantics:

- `conversation_id` — resume with `--conversation <id>`. **The
  envelope value the v0.2.0 reference claimed was missing.**
- `status` — `"SUCCESS"` (or failure status). Use this, **not** the
  process exit code, to detect completion: `agy -p` exits 0 on partial
  completion too.
- `response` — the model reply. Multi-line strings are valid JSON
  (escape sequences are preserved). For scripted pipelines, parse the
  envelope and read `.response`; do not parse stdout as prose.
- `duration_seconds` — wall-clock time for the run.
- `num_turns` — agent turn count (default 1 for single-shot).
- `usage` — token accounting with `cache_read_tokens` for prompt-cache
  attribution. Multiply by the model's per-token cost (or note the
  free tier for Gemini) to get the actual run cost.

### `stream-json`

Newline-delimited JSON events for line-buffered consumers that want
progress as the agent thinks. Event types include `init`, `step_update`,
and a terminal `result`. Each `step_update` carries a `tool_info`
object (canonical tool name, parameters, output) and a `subagent_info`
payload (including `conversation_id` and `log_uri`) for delegated
subagents. Pair with `--json-schema <schema-or-path>` to enforce
structure on the final `result` event — the schema accepts an inline
string or a path to a JSON-Schema file.

This is the right shape for CI/eval harnesses, progress UIs, and
incremental log shipping. It supersedes the prior "no result
envelope" assumption from `agy` versions before 1.1.8.

## Auth + quota

- **OS keyring first.** `agy` reads the saved Google OAuth token from
  the OS keychain; no env vars needed.
- **No keyring → browser OAuth.** `agy -i` triggers a browser flow;
  sign in with the Google account that holds the AI Pro subscription.
- **Silent auth race.** The first cache refresh after launch can
  race the keyring read and emit
  `error getting token source: You are not logged into Antigravity`
  in the log. The follow-up `Print mode: silent auth succeeded` line
  is the success marker. **Pattern to recognize:** the auth-error
  line + the `silent auth succeeded` line in the same run = a
  non-fatal transient. If only the error line repeats with no
  recovery, the keyring is genuinely empty.
- **Quota:** Gemini runs against the AI Pro quota on the
  `cloudcode-pa.googleapis.com` backend (consumer subscription tier,
  NOT the public Gemini API that resets at midnight Pacific). When
  exhausted, agy returns `RESOURCE_EXHAUSTED (429)` with gRPC reason
  `QUOTA_EXHAUSTED` — a long window (hours), distinct from
  `RATE_LIMIT_EXCEEDED` (short RPM window). See **Quota exhaustion**
  below for the full surface, especially for image generation.
- **Auth context from the log:****
  `keyringAuth: loaded token, expiry=...` confirms a saved token;
  `ChainedAuth: authenticated via keyring` confirms the active
  session; `applyAuthResult: email=<gmail>, authMethod=consumer,
  quotaProject=` confirms the consumer (subscription) tier.
- **WSL:** token storage is file-based; auth issues are local-file
  problems, not browser-only problems.

To rotate credentials: `agy -i` → `/logout` → `agy -i` again to
re-trigger browser OAuth.

To script: do not script `/logout`; the OAuth flow needs a real
browser, so token refresh happens interactively.

## Quota exhaustion (especially image generation)

`agy`'s quota lives on `cloudcode-pa.googleapis.com` (Google AI Pro /
Google One consumer tier), not the public Gemini API. The critical
difference:

- **`RATE_LIMIT_EXCEEDED`** = short window (seconds/minutes, RPM).
- **`QUOTA_EXHAUSTED`** = long window (hours, per-model). agy does
  NOT retry this — it's non-transient to the CLI's retry logic.

### Image generation — the hidden model

`agy models` lists only reasoning models (Gemini 3.x flash, Claude,
gpt-oss). **Image generation runs on `gemini-3.1-flash-image`
under the hood, regardless of which `--model` you pass.** Switching
`--model` to a different reasoning tier does NOT change the image
model or its quota — they share one per-model cap. Passing
`--model gemini-2.5-flash-image` directly is rejected (`invalid model
selection`); agy's whitelist doesn't expose image models.

### The 429 envelope (parse it, don't guess)

The `RESOURCE_EXHAUSTED` error in `~/.gemini/antigravity-cli/log/cli-*.log`
carries structured gRPC details you can parse to schedule retries:

```json
{"code": 429, "status": "RESOURCE_EXHAUSTED",
 "details": [{"@type": "...google.rpc.ErrorInfo",
   "reason": "QUOTA_EXHAUSTED",
   "domain": "cloudcode-pa.googleapis.com",
   "metadata": {"model": "gemini-3.1-flash-image",
     "quotaResetDelay": "4h52m2.787s",
     "quotaResetTimeStamp": "2026-07-29T09:29:33Z"}}]}
```

- `quotaResetTimeStamp` — when the cap drains (UTC). Wait until then
  + 60s margin before retrying.
- `quotaResetDelay` — human-readable window (~5h observed).
- `model` — which model is exhausted (per-model, not global).

### Empirical caps (observed, not official)

- **Image gen:** ~10-12 calls per ~5h window, then `QUOTA_EXHAUSTED`.
  12 calls in ~3 min exhausted it; 8 retries with different
  `--model` values all failed (same underlying image model).
- **Reasoning models:** higher caps, but the same `QUOTA_EXHAUSTED`
  mechanism applies. Check the log for the reset timestamp before
  bulk retrying.

### Workarounds (ranked)

1. **Wait for `quotaResetTimeStamp` + throttle.** Parse the last 429's
   `quotaResetTimeStamp`, sleep until then + 60s, then retry with
   `sleep 30` between calls. Cap batches at ~10 image calls per window.
2. **Fall back to OpenRouter (same model, pay-per-use) — requires user
   approval.** `google/gemini-3.1-flash-image` is the exact model agy
   uses under the hood, available on OpenRouter at ~$0.50/M in,
   $3.00/M out — no subscription cap, pay per use. Cheaper sibling
   `google/gemini-2.5-flash-image` (~$0.30/$2.50) also works. **Gate:
   surface the cost estimate to the user and get explicit approval before
   switching** — OR billing is separate from the AI Pro subscription and
   shouldn't switch silently. Never block the user without options:
   present this as a choice (wait ~5h for free, OR pay ~$X now).
3. **Route non-image parts to the host harness** if only the image step
   needs Gemini. For non-image tasks, use Andrés's favorites (Kimi K3,
   GLM 5.2, DeepSeek V4 Pro) via the host harness's model routing.
4. **Gemini API direct** (pay-per-use API key from aistudio.google.com)
   with `imagen-4.0-generate` — ~$0.04/image, quota typically 100x
   higher. Separate billing from the AI Pro subscription.
5. **Stock photos** (Unsplash/Pexels) if the images don't need to be
   AI-generated — free, offline-safe.

### Detecting exhaustion before it bites

Before a bulk image-gen run, tail the latest log and grep for
`QUOTA_EXHAUSTED`:
```bash
grep -l QUOTA_EXHAUSTED ~/.gemini/antigravity-cli/log/cli-*.log |
  tail -1 | xargs grep -o '"quotaResetTimeStamp"[^,]*'
```
If the reset timestamp is in the future, wait. If absent, the quota
is live and you can proceed (still throttle).

## Agent (custom) registration

`agy agents` lists custom agents. On a clean install it returns
`Available agents:` (empty). Agents are defined via Markdown files
under `~/.gemini/antigravity-cli/agents/` or via the dynamic
`define_subagent` flow (1.1.6+). They're not a daily concern for
`agy -p` work — `--agent <name>` is the only flag that references
them.

## See also

- `SKILL.md` — mental model, delegation patterns, pitfalls, verification
- `commands.md` — quick reference tables
- `workflows.md` — worked sequences (one-shot, batch, second-opinion, log triage)
- `agent-launchers.md` — harness-specific launchers
