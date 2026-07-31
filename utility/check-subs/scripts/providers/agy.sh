#!/usr/bin/env bash
# providers/agy.sh — probe Google AI Pro (via antigravity-cli CLI `agy`).
#
# v1: liveness only. The `agy` CLI does not expose a quota subcommand, and
# its OAuth token is stored in the macOS keychain (not a plain file). For v1
# we just call the CLI with a 1-token prompt on the cheapest model and check
# the response.
#
# v1.1 plan (see references/agy-quota.md): implement the OAuth dance against
# https://cloudcode-pa.googleapis.com using the public antigravity-cli client
# (CLIENT_ID 1071006060591-... .apps.googleusercontent.com). The endpoint
# returns per-model quotaInfo.remainingFraction + quotaInfo.resetTime
# (5h + weekly windows confirmed).
#
# Probe command: agy --model gemini-3.5-flash-low --effort low --print "ping"
# We disable thinking (--effort low) per the design decision: no need to think
# just to check if alive.
#
# Outputs a JSON block on stdout (or "null" on error).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib.sh
source "$SCRIPT_DIR/../lib.sh"

probe() {
  if ! command -v agy >/dev/null 2>&1; then
    log_warn "agy: CLI not in PATH"
    printf '%s' '{"status":"not-configured","api":"agy CLI","comment":"install antigravity-cli CLI and authenticate"}'
    return 0
  fi

  local start elapsed resp rc
  start=$(date +%s)
  resp="$(agy --model gemini-3.5-flash-low --effort low --print-timeout 15s --print "ping" 2>&1)" || rc=$?
  elapsed=$(( $(date +%s) - start ))

  if [ "${rc:-0}" -ne 0 ]; then
    if printf '%s' "$resp" | grep -qiE 'resource exhausted|quota|429|rate'; then
      log_info "agy: quota-exhausted signal detected"
      printf '%s' '{"status":"ok","api":"agy CLI (liveness only)","liveness":{"alive":true,"signal":"quota-exhausted"},"quota_signal":"quota-exhausted-text","comment":"v1: liveness only; v1.1 will read full quota via cloudcode-pa"}'
      return 0
    fi
    log_warn "agy: probe failed (rc=$rc)"
    printf '%s' "{\"status\":\"network-error\",\"api\":\"agy CLI\",\"rc\":$rc}"
    return 0
  fi

  # Heuristic: alive if we got a non-empty response in reasonable time.
  if [ -n "$resp" ] && [ "$elapsed" -lt 15 ]; then
    log_info "agy: alive (${elapsed}s)"
    printf '%s' '{"status":"ok","api":"agy CLI (liveness only)","liveness":{"alive":true,"last_ok":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},"quota_signal":"none","comment":"v1: liveness only; v1.1 will read full quota via cloudcode-pa"}'
  else
    log_warn "agy: empty response or slow (${elapsed}s)"
    printf '%s' '{"status":"timeout","api":"agy CLI (liveness only)"}'
  fi
}

probe
