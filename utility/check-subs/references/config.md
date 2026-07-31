# Configuration

`check-subs` reads configuration in this priority order:

1. **Config file** at `$XDG_CONFIG_HOME/check-subs/config.json` (default `~/.config/check-subs/config.json`).
2. **Environment variables** (overrides file values).
3. **Harness fallback** (read-only, never writes back). Looks for these auth files in order:
   - `~/.pi/agent/auth.json`
   - `~/.claude/auth.json`
   - other common locations

The fallback lets `check-subs` work out of the box on a machine that already
has auth configured for another harness, without the user having to set up a
second config file.

## Schema (v1)

```jsonc
{
  // OpenRouter (pay-per-use)
  "openrouter": {
    "apiKey": "sk-or-v1-..."           // env: OPENROUTER_API_KEY
  },

  // opencode-go Go (subscription, session-cookie auth)
  "opencode-go": {
    "workspaceId": "...",              // env: OPENCODE_GO_WORKSPACE_ID
    "authCookie":  "auth=...",         // env: OPENCODE_GO_AUTH_COOKIE  (raw cookie value, not the "auth=" prefix)
    "apiKey":      "sk-zi..."          // env: OPENCODE_GO_API_KEY  (optional; only used for inference API, not for quota scrape)
  },

  // MiniMax (subscription, bearer auth)
  "minimax": {
    "apiKey": "sk-cp-..."              // env: MINIMAX_API_KEY
  },

  // Google AI Pro (no config — uses `agy` CLI's authenticated session)

  // Optional: override per-window thresholds (defaults from SKILL.md).
  "thresholds": {
    "5h":      { "warn": 70, "danger": 85 },
    "weekly":  { "warn": 75, "danger": 90 },
    "monthly": { "warn": 80, "danger": 95 }
  }
}
```

## Minimal viable config

```json
{
  "openrouter": { "apiKey": "sk-or-v1-..." },
  "minimax":    { "apiKey": "sk-cp-..." }
}
```

OG needs `workspaceId` and `authCookie` from the user's browser session (log
into `https://opencode.ai/workspace/<id>/go` once, then copy the `auth`
cookie value from devtools). Without them, `check-subs probe opencode-go`
returns `not-configured` and the other 3 providers still work.

AGY requires no config — install the `agy` CLI and authenticate once with
Google sign-in. After that, `check-subs probe agy` runs liveness probes.

## How to get the OG cookie

1. Open `https://opencode.ai/workspace/<your-workspace-id>/go` in a browser and sign in.
2. DevTools → Application → Cookies → `opencode.ai` → find the `auth` cookie.
3. Copy its value (a JWT-looking string).
4. Put it in `config.json` as `opencode-go.authCookie` (raw value, no `auth=` prefix).
5. The `workspaceId` is in the URL.

## Fallback behavior

If `openrouter.apiKey` is not in the config file or env, the script looks
for `openrouter.key` in `~/.pi/agent/auth.json`. This makes the skill work on
machines that already have pi-style auth without forcing a second config.

The fallback is **read-only**. `check-subs` never modifies the harness's auth
file. If you want to "promote" a fallback value to a real config, copy it
manually.

## Inspection

Run `check-subs config` to see all resolved values (keys masked).
