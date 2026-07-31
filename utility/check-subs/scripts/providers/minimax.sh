#!/usr/bin/env bash
# providers/minimax.sh — probe MiniMax subscription quota.
#
# Endpoint: GET https://api.minimax.io/v1/token_plan/remains
# Auth:     Bearer <MINIMAX_API_KEY>
# Response: {model_remains:[{model_name, current_interval_*, current_weekly_*}],
#            base_resp:{status_code, status_msg}}
#
# Reuses the response schema and "general" model selection from
# clankercode/pi-quota-monitor.
#
# Per-window fields (in seconds/ms):
#   current_interval_remaining_percent  — 5h window remaining
#   current_interval_status             — 0/1/etc.
#   remains_time                        — seconds until 5h window reset
#   end_time                            — epoch ms of 5h window end
#   current_weekly_remaining_percent    — weekly window remaining
#   current_weekly_status               — weekly status
#   weekly_remains_time                 — seconds until weekly reset
#   weekly_end_time                     — epoch ms of weekly window end
#
# consumed = 100 - remainingPercent (per SPEC §V.4).
# Prefers the "general" model entry when present.
#
# Outputs a JSON block on stdout (or "null" on error).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib.sh
source "$SCRIPT_DIR/../lib.sh"

probe() {
  local key; key="$(resolve minimax apiKey MINIMAX_API_KEY)"
  if [ -z "$key" ]; then
    log_warn "minimax: no apiKey configured"
    printf '%s' '{"status":"not-configured","api":"GET /v1/token_plan/remains"}'
    return 0
  fi

  local resp http_code
  resp="$(curl -sS --max-time 10 -w '\n%{http_code}' \
    -H "Authorization: Bearer $key" \
    -H "Content-Type: application/json" \
    "https://api.minimax.io/v1/token_plan/remains" 2>/dev/null)" || {
      log_warn "minimax: network error"
      printf '%s' '{"status":"network-error","api":"GET /v1/token_plan/remains"}'
      return 0
    }
  http_code="$(printf '%s' "$resp" | tail -1)"
  resp="$(printf '%s' "$resp" | sed '$d')"

  if [ "$http_code" != "200" ]; then
    log_warn "minimax: HTTP $http_code"
    printf '%s' "{\"status\":\"auth-error\",\"api\":\"GET /v1/token_plan/remains\",\"http_code\":$http_code}"
    return 0
  fi

  # Parse the response. Prefer "general" entry; fall back to first.
  # NOTE: end_time, remains_time, weekly_end_time, weekly_remains_time are all
  # in MILLISECONDS in the API response (despite the "time" suffix on the
  # remaining fields). We treat them as ms and convert to seconds for jq's
  # `todate`. consumedPercent = 100 - remainingPercent.
  echo "$resp" | jq -c '
    if .base_resp.status_code != 0 then
      {status:"auth-error", api:"GET /v1/token_plan/remains", base_resp: .base_resp}
    else
      (.model_remains // []) as $list |
      ([$list[] | select(.model_name == "general")] | first // $list[0]) as $g |
      if $g == null then
        {status:"parse-error", api:"GET /v1/token_plan/remains", comment:"empty model_remains"}
      else
        {
          status: "ok",
          api: "GET /v1/token_plan/remains",
          kind: "subscription",
          windows: {
            "5h": {
              key: "5h",
              consumedPercent: (100 - ($g.current_interval_remaining_percent // 0)),
              resetEtaMs: ($g.remains_time // 0),
              resetAt: (if $g.end_time then (($g.end_time / 1000) | todate) else null end),
              status: ("ok")
            },
            "weekly": {
              key: "weekly",
              consumedPercent: (100 - ($g.current_weekly_remaining_percent // 0)),
              resetEtaMs: ($g.weekly_remains_time // 0),
              resetAt: (if $g.weekly_end_time then (($g.weekly_end_time / 1000) | todate) else null end),
              status: ("ok")
            }
          }
        }
      end
    end
  ' 2>/dev/null || {
    log_warn "minimax: parse error"
    printf '%s' '{"status":"parse-error","api":"GET /v1/token_plan/remains"}'
  }
}

probe
