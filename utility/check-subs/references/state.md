# State File

The state file at `$XDG_STATE_HOME/check-subs/state.json` (default
`~/.local/state/check-subs/state.json`) is the single source of truth for
subscription liveness and quota. Any harness can read it; `check-subs` writes
it atomically.

## Schema (v2)

```jsonc
{
  "schema_version": 2,
  "updated_at": "2026-07-31T03:14:00Z",
  "ttl_s": 300,                          // default freshness window

  "providers": {
    "openrouter": {
      "status": "ok",                    // ok | not-configured | auth-error | network-error | parse-error | timeout
      "kind": "pay-per-use",
      "api": "GET /api/v1/auth/key",
      "credits": {
        "usage": 135.90,
        "usage_daily": 0.32,
        "usage_weekly": 36.72,
        "usage_monthly": 108.35,
        "limit": null,
        "limit_remaining": null,
        "limit_reset": "monthly",
        "is_free_tier": false,
        "expires_at": null
      },
      "next_probe_at": "2026-07-31T03:19:00Z"
    },

    "opencode-go": {
      "status": "ok",
      "kind": "subscription",
      "api": "GET /workspace/{id}/go (HTML scrape)",
      "windows": {
        "5h":      { "key": "5h",      "consumedPercent": 12, "resetEtaMs": 14523000, "resetAt": "2026-07-31T08:00:00Z", "status": "ok" },
        "weekly":  { "key": "weekly",  "consumedPercent": 35, "resetEtaMs": 432000000, "resetAt": "2026-08-06T03:14:00Z", "status": "ok" },
        "monthly": { "key": "monthly", "consumedPercent": 60, "resetEtaMs": 864000000, "resetAt": "2026-08-31T03:14:00Z", "status": "ok" }
      },
      "next_probe_at": "2026-07-31T08:00:00Z"     // pushed out to earliest reset
    },

    "minimax": {
      "status": "ok",
      "kind": "subscription",
      "api": "GET /v1/token_plan/remains",
      "windows": {
        "5h":     { "key": "5h",     "consumedPercent": 45, "resetEtaMs": 8200000,  "resetAt": "2026-07-31T05:00:00Z", "status": "ok" },
        "weekly": { "key": "weekly", "consumedPercent": 70, "resetEtaMs": 518400000,"resetAt": "2026-08-06T03:14:00Z", "status": "ok" }
      },
      "next_probe_at": "2026-07-31T05:00:00Z"
    },

    "agy": {
      "status": "ok",
      "api": "agy CLI (liveness only)",
      "liveness": { "alive": true, "last_ok": "2026-07-31T03:14:00Z" },
      "quota_signal": "none",
      "comment": "v1: liveness only; v1.1 will read full quota via cloudcode-pa",
      "next_probe_at": "2026-07-31T03:19:00Z"   // default cadence, no signal to defer
    }
  }
}
```

## Status taxonomy

| Status | Meaning |
|---|---|
| `ok` | probe succeeded; data is fresh |
| `not-configured` | required config (apiKey / workspaceId / authCookie) is missing |
| `auth-error` | HTTP 401/403 or cookie expired; user must re-auth |
| `network-error` | curl/connection failure; probe will be retried |
| `parse-error` | HTTP 200 but the response shape didn't match expectations |
| `timeout` | probe took longer than the 15s budget |
| `exhausted` | window-specific; recorded via `check-subs record` after a real 429 |

## Freshness

`next_probe_at` is set by the probe to the earliest known reset time + the
default cadence (whichever is later, with a 5-min floor). Consumers can
compare `now` against `next_probe_at` to decide whether the state is fresh
or stale.

A provider that just hit its 5H cap will have `next_probe_at` ~5 hours in
the future, not 5 minutes. Other providers continue to be probed on the
normal cadence.

## Atomic writes

`check-subs` writes via `tmp + rename`. Multiple consumers can read the file
at any time without seeing partial data. Writes happen on:
- `check-subs probe` (each provider's block is merged in)
- `check-subs record` (post-dispatch update)

The file is overwritten in place, not appended. The debug log at
`$STATE_DIR/debug.log` IS appended, with 60-min retention.
