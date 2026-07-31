#!/usr/bin/env bash
# providers/or.sh — probe OpenRouter quota.
#
# Endpoint: GET https://openrouter.ai/api/v1/auth/key
# Auth:     Bearer <OPENROUTER_API_KEY>
# Response: {data:{usage, usage_daily, usage_weekly, usage_monthly,
#                    limit, limit_remaining, is_free_tier, expires_at}}
#
# Outputs a JSON block on stdout (or "null" on error).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib.sh
source "$SCRIPT_DIR/../lib.sh"

probe() {
  local key; key="$(resolve openrouter apiKey OPENROUTER_API_KEY)"
  if [ -z "$key" ]; then
    log_warn "or: no apiKey configured"
    printf '%s' '{"status":"not-configured","api":"GET /api/v1/auth/key"}'
    return 0
  fi

  local resp http_code
  resp="$(curl -sS --max-time 10 -w '\n%{http_code}' \
    -H "Authorization: Bearer $key" \
    -H "Accept: application/json" \
    "https://openrouter.ai/api/v1/auth/key" 2>/dev/null)" || {
      log_warn "or: network error"
      printf '%s' '{"status":"network-error","api":"GET /api/v1/auth/key"}'
      return 0
    }
  http_code="$(printf '%s' "$resp" | tail -1)"
  resp="$(printf '%s' "$resp" | sed '$d')"

  if [ "$http_code" != "200" ]; then
    log_warn "or: HTTP $http_code"
    jq -c --arg code "$http_code" '{status:"auth-error", api:"GET /api/v1/auth/key", http_code:$code}' <<<'null' >/dev/null 2>&1 || true
    printf '%s' "{\"status\":\"auth-error\",\"api\":\"GET /api/v1/auth/key\",\"http_code\":$http_code}"
    return 0
  fi

  # Parse and reduce to a stable shape.
  echo "$resp" | jq -c '{
    status: "ok",
    api: "GET /api/v1/auth/key",
    kind: "pay-per-use",
    credits: {
      usage:            .data.usage,
      usage_daily:      .data.usage_daily,
      usage_weekly:     .data.usage_weekly,
      usage_monthly:    .data.usage_monthly,
      limit:            .data.limit,
      limit_remaining:  .data.limit_remaining,
      limit_reset:      .data.limit_reset,
      is_free_tier:     .data.is_free_tier,
      expires_at:       .data.expires_at
    }
  }' 2>/dev/null || {
    log_warn "or: parse error"
    printf '%s' '{"status":"parse-error","api":"GET /api/v1/auth/key"}'
  }
}

probe
