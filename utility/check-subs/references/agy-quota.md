# AGY full quota — v1.1 plan

v1 of `check-subs probe agy` is **liveness only** — it calls the `agy` CLI
with a 1-token prompt and reports alive/dead. The v1 design choice was:
"no need to think just to check if alive" (cheapest model, no reasoning).

v1.1 will add the **full quota** read for Google AI Pro, matching the depth
of the other 3 providers (5h + weekly windows with `consumedPercent` and
`resetAt`).

## Why v1 doesn't do this

- `agy` has no `quota` subcommand (verified)
- `agy`'s OAuth token is stored in the macOS keychain (not a plain file
  accessible from a shell script)
- The full-quota endpoint requires an OAuth Bearer token; the `agy` binary
  holds the token internally but doesn't expose it

## The v1.1 mechanism

Use the same `cloudcode-pa.googleapis.com` endpoint that other OSS tools use
(andyvandaric/opencode-ag-auth, Dinujaya-Sandaruwan/antigravity-cli-QuotA,
frieser/opencode-antigravity-quota, gyozalab/QuotaGem):

### Step 1 — discover project ID

```
POST https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist
Authorization: Bearer <access_token>
Content-Type: application/json
User-Agent: antigravity/1.18.3 darwin/arm64

{"metadata": {"ideType": "ANTIGRAVITY", "platform": "PLATFORM_UNSPECIFIED", "pluginType": "GEMINI"}}

→ 200 {"cloudaicompanionProject": "<id>"}
   (or {"cloudaicompanionProject": {"id": "<id>"}})
```

If the user is signed in to `agy`, the access token can be extracted from
the macOS keychain:

```bash
security find-generic-password -s "antigravity-cli" -w
# or, depending on keychain layout:
security find-generic-password -s "antigravity-cli" -w
```

(Exact service name TBD — the keychain entry name needs to be discovered by
running `security dump-keychain | grep -i antigrav` once on a real
authenticated machine.)

### Step 2 — fetch quota

```
POST https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels
Authorization: Bearer <access_token>
Content-Type: application/json

{"project": "<id>"}

→ 200 {
  "models": {
    "gemini-3.1-pro": {
      "displayName": "Gemini 3.1 Pro",
      "quotaInfo": { "remainingFraction": 0.5, "resetTime": "2026-07-31T08:00:00Z" }
    },
    "gemini-3.6-flash": { "...": "..." }
  }
}
```

### Step 3 — fold into state

Map the response to the unified state shape:

| API field | State field |
|---|---|
| `remainingFraction` | `consumedPercent = (1 - remainingFraction) * 100` |
| `resetTime` (RFC3339) | `resetAt`; `resetEtaMs = resetTime - now` |

Since Google AI Pro has the same 5h + weekly window structure as OG and
MiniMax, the state file shape is unchanged — v1.1 just populates the
`windows` block for `agy`.

## Auth setup on a fresh machine

If the keychain has no `antigravity-cli` entry (the user has never run
`agy`), the v1.1 path is `not-configured` and falls back to v1 liveness
mode. To bootstrap, the user runs `agy --print "hello"` once, completes
the Google sign-in flow, and the keychain gets populated.

## v1.1 alternative — local antigravity-cli IDE gRPC probe

If the antigravity-cli desktop app is running on `localhost`, there's a second
mechanism (gyozalab/QuotaGem uses it): discover the port + CSRF token
from the running process's CLI flags, then POST to
`http://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/{method}`
with `X-Codeium-Csrf-Token: <csrf>`.

This is read-only and doesn't consume quota, but it requires the IDE to be
running. Not useful for headless `agy`-only setups. v1.1 will prefer the
cloudcode-pa approach and only fall back to the local gRPC probe if
cloudcode-pa fails.

## Reference implementations

- `andyvandaric/opencode-ag-auth/scripts/check-quota.mjs` — 218 lines, the gold-standard JS reference
- `Dinujaya-Sandaruwan/antigravity-cli-QuotA/internal/api/client.go` — same flow in Go
- `frieser/opencode-antigravity-quota` — TS opencode-go plugin
- `gyozalab/QuotaGem/src-tauri/src/providers/antigravity.rs` — Rust, with the local gRPC probe as a bonus
