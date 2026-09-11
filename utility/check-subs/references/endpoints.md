# Endpoints

Detailed reference for each provider's quota endpoint. The `check-subs` script
calls these directly; this doc is for maintainers and integrators.

## OpenRouter

| | |
|---|---|
| **Endpoint** | `GET https://openrouter.ai/api/v1/auth/key` |
| **Auth** | `Authorization: Bearer <OPENROUTER_API_KEY>` |
| **Response** | `{data: {usage, usage_daily, usage_weekly, usage_monthly, limit, limit_remaining, limit_reset, is_free_tier, expires_at}}` |
| **Notes** | `/api/v1/credits` also exists (total credits only); `/auth/key` is strictly more useful. On 429 the response carries `X-RateLimit-Limit/Remaining/Reset` + `Retry-After`. |
| **Source** | https://openrouter.ai/docs/api_reference/limits.md |

## opencode-go Go

| | |
|---|---|
| **Endpoint** | `GET https://opencode.ai/workspace/{workspaceId}/go` |
| **Auth** | `Cookie: auth=<authCookie>` (session cookie from OAuth login — NOT an API key) |
| **User-Agent** | Desktop browser UA (any modern one) |
| **Response** | SSR HTML with embedded `{rollingUsage,weeklyUsage,monthlyUsage}:$R[N]={status:"ok",resetInSec:N,usagePercent:N}` |
| **Window map** | `rollingUsage`→5h, `weeklyUsage`→weekly, `monthlyUsage`→monthly |
| **Notes** | No JSON API; quota is hidden in the dashboard HTML. No `X-RateLimit-*` headers on 200. On 429 the body has `metadata.limitName` = `"5 hour"` / `"weekly"` / `"monthly"`. The `opencode-go` API key works for inference API (`/v1/models`, `/zen/go/v1/...`) but does NOT work for the dashboard. |
| **Source** | Regex pattern from slkiser/opencode-quota v4.4.0; dashboard at opencode.ai/docs/go |

## MiniMax

| | |
|---|---|
| **Endpoint** | `GET https://api.minimax.io/v1/token_plan/remains` |
| **Auth** | `Authorization: Bearer <MINIMAX_API_KEY>` |
| **Response** | `{model_remains: [{model_name, current_interval_*, current_weekly_*}], base_resp: {status_code, status_msg}}` |
| **Per-window fields** | 5h: `current_interval_remaining_percent`, `remains_time` (sec), `end_time` (epoch ms), `current_interval_status`. Weekly: same shape with `current_weekly_` prefix. |
| **Model selection** | Prefer the `"general"` entry; fall back to first. |
| **Consumed math** | `consumedPercent = 100 - remainingPercent` |
| **Notes** | On 2056 (usage limit exceeded), the `remains_time` for that window is the seconds until reset. Other relevant error codes: 1002 (rate limit), 1008 (insufficient balance), 2045 (rate growth), 2049 (invalid key). |
| **Source** | clankercode/pi-quota-monitor; platform.minimax.io/docs/api-reference/errorcode.md |

## Probing model per provider (cheapest, no thinking)

| Provider | Probe model | Why |
|---|---|---|
| opencode-go Go | `deepseek-v4-flash` | cheapest on OG |
| MiniMax | `M 2.7 High Speed` | cheapest on the sub |

OpenRouter is not probed (assume credits present); `check-subs probe openrouter` only reads the `/auth/key` endpoint.
