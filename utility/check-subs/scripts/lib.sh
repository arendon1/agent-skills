#!/usr/bin/env bash
# lib.sh — shared helpers for check-subs.
#
# Provides: logging, atomic state IO, masked-key handling, retry-with-backoff,
# JSON querying via jq, threshold evaluation.
#
# Compatibility: uses only POSIX sh + bash 3.2 (Apple's /bin/bash). No
# associative arrays (introduced in bash 4). Thresholds and provider metadata
# are exposed via lookup functions.

set -euo pipefail

# ---- paths -----------------------------------------------------------------

: "${XDG_CONFIG_HOME:=$HOME/.config}"
: "${XDG_STATE_HOME:=$HOME/.local/state}"

CONFIG_DIR="$XDG_CONFIG_HOME/check-subs"
CONFIG_FILE="$CONFIG_DIR/config.json"
STATE_DIR="$XDG_STATE_HOME/check-subs"
STATE_FILE="$STATE_DIR/state.json"
LOG_FILE="$STATE_DIR/debug.log"

mkdir -p "$STATE_DIR" "$CONFIG_DIR" 2>/dev/null || true

# ---- threshold + provider lookups (no assoc arrays for bash 3.2 compat) ---

# Unified per-window thresholds. Same values across all providers.
# (5h: faster reset, warn earlier; weekly: mid; monthly: only near exhaustion.)
get_warn() {
  case "$1" in
    5h) echo 70 ;;
    weekly) echo 75 ;;
    monthly) echo 80 ;;
    *) echo 70 ;;
  esac
}
get_danger() {
  case "$1" in
    5h) echo 85 ;;
    weekly) echo 90 ;;
    monthly) echo 95 ;;
    *) echo 85 ;;
  esac
}

# Cheapest probe model per provider.
get_probe_model() {
  case "$1" in
    opencode-go) echo "deepseek-v4-flash" ;;
    minimax)     echo "m2.7-highspeed" ;;
    agy)         echo "gemini-3.5-flash-low" ;;
    *) echo "" ;;
  esac
}

# Probe kind: subscription has windows, pay-per-use has credits, agy is liveness.
get_kind() {
  case "$1" in
    opencode-go) echo "subscription" ;;
    minimax)     echo "subscription" ;;
    openrouter)  echo "pay-per-use" ;;
    agy)         echo "liveness" ;;
    *) echo "" ;;
  esac
}

# Windows exposed by each provider.
get_windows() {
  case "$1" in
    opencode-go) echo "5h weekly monthly" ;;
    minimax)     echo "5h weekly" ;;
    *) echo "" ;;
  esac
}

# ---- logging ---------------------------------------------------------------

_log() {
  local level="$1"; shift
  local ts; ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local line="[$ts] [$level] $*"
  printf '%s\n' "$line" >&2
  mkdir -p "$STATE_DIR" 2>/dev/null || true
  printf '%s\n' "$line" >> "$LOG_FILE" 2>/dev/null || true
  # Retention: if the log is non-empty and the first line is older than 60 min, truncate.
  if [ -s "$LOG_FILE" ]; then
    local cutoff first_ts
    cutoff="$(date -u -v-60M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
              || date -u -d '60 minutes ago' +%Y-%m-%dT%H:%M:%SZ)"
    first_ts="$(head -1 "$LOG_FILE" | cut -d']' -f1 | tr -d '[')"
    if [ -n "$first_ts" ] && [ "$first_ts" \< "$cutoff" ] 2>/dev/null; then
      : > "$LOG_FILE"
    fi
  fi
}

log_info()  { _log INFO  "$@"; }
log_warn()  { _log WARN  "$@"; }
log_error() { _log ERROR "$@"; }
log_debug() { [ "${CHECK_SUBS_DEBUG:-0}" = "1" ] && _log DEBUG "$@" || true; }

# ---- atomic state IO -------------------------------------------------------

ensure_state_dir() { mkdir -p "$STATE_DIR" "$CONFIG_DIR"; }

# Read a jq expression against the state file. Empty/missing file = empty obj.
state_get() {
  local expr="$1"
  [ -f "$STATE_FILE" ] || { printf '{}'; return 0; }
  jq -c "$expr" "$STATE_FILE" 2>/dev/null || printf '{}'
}

# Atomic write: write to .tmp, rename. Other readers never see partial.
state_set() {
  local json="$1"
  ensure_state_dir
  local tmp="$STATE_FILE.tmp.$$"
  printf '%s\n' "$json" > "$tmp"
  mv -f "$tmp" "$STATE_FILE"
}

# Merge a provider's update into the state. Args: provider_key, json_obj.
# Computes next_probe_at: if the block has window resetEtaMs values, push the
# next probe to the earliest reset time (floor 5 min). Otherwise 5 min cadence.
state_merge_provider() {
  local provider="$1"
  local block="$2"
  [ -z "$block" ] || [ "$block" = "null" ] && return 0
  ensure_state_dir
  local now; now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local current; current="$(state_get '.')"
  # Note: jq 1.8 has a parser quirk where //= and = can't coexist in the same
  # expression. We use explicit if/else for the schema_version field.
  # next_probe_at:
  #   - If the block has its own next_probe_at, use it (e.g. cmd_record).
  #   - Else if the block has windows with resetEtaMs, push to the earliest
  #     reset (floor 5 min).
  #   - Else (pay-per-use or no windows), 5-min cadence.
  echo "$current" | jq --arg p "$provider" --arg now "$now" --argjson b "$block" '
    .schema_version = (if has("schema_version") then .schema_version else 2 end)
    | .updated_at = $now
    | .ttl_s = 300
    | .providers[$p] = (
        $b + {
          next_probe_at: (
            if $b.next_probe_at then $b.next_probe_at
            elif ($b.windows // null) then (
              ([$b.windows | to_entries[] | (.value.resetEtaMs // 999999999)] | min) as $eta_ms |
              (if $eta_ms < 300000 then 300000 else $eta_ms end) as $cap_ms |
              ($now | fromdateiso8601) as $now_sec |
              (($cap_ms / 1000) | floor) as $eta_sec |
              ($now_sec + $eta_sec) | todate
            )
            else
              ($now | fromdateiso8601 + 300 | todate)
            end
          )
        }
      )
  ' > "$STATE_FILE.tmp.$$"
  mv -f "$STATE_FILE.tmp.$$" "$STATE_FILE"
}

# ---- masked-key handling ---------------------------------------------------

mask_key() {
  local k="$1"
  [ -z "$k" ] && { printf ''; return; }
  local n=${#k}
  [ "$n" -le 12 ] && { printf '***'; return; }
  printf '%s...%s' "${k:0:10}" "${k: -4}"
}

# ---- retry with exponential backoff ----------------------------------------

# retry <max_attempts> <initial_delay_s> <description> -- command...
# Backoff: 1s, 3s, 9s, 27s, 81s (5 retries).
retry() {
  local max="${1:-5}"
  local initial="${2:-1}"
  local desc="${3:-operation}"
  shift 3
  local delay=$initial
  local attempt=1
  local rc=0
  while [ "$attempt" -le "$max" ]; do
    if "$@"; then
      return 0
    fi
    rc=$?
    if [ "$attempt" -eq "$max" ]; then
      log_warn "$desc failed after $attempt attempts (rc=$rc)"
      return $rc
    fi
    log_debug "$desc attempt $attempt failed; sleeping ${delay}s"
    sleep "$delay"
    delay=$((delay * 3))
    attempt=$((attempt + 1))
  done
  return $rc
}

# ---- threshold classifier --------------------------------------------------

# Returns "ok" | "warn" | "danger" for a (consumedPercent, window) pair.
classify() {
  local pct="$1" window="$2"
  local w d
  w="$(get_warn "$window")"
  d="$(get_danger "$window")"
  if [ "$pct" -ge "$d" ] 2>/dev/null; then printf 'danger'
  elif [ "$pct" -ge "$w" ] 2>/dev/null; then printf 'warn'
  else printf 'ok'
  fi
}

# ---- config reading --------------------------------------------------------

# Read a key from the config file (jq). Returns empty string if missing.
# Pass the path as a jq expression that uses bracket notation for keys with
# dashes, e.g. config_get '."opencode-go".workspaceId'.
config_get() {
  local path="$1"
  [ -f "$CONFIG_FILE" ] || return 0
  jq -r "$path // empty" "$CONFIG_FILE" 2>/dev/null
}

# Fallback: try common harness-specific auth files (READ-ONLY).
# Looks for openrouter.key, opencode-go.{key,workspaceId,authCookie}, minimax.key.
fallback_auth() {
  local provider="$1" field="$2"
  local candidate_paths=(
    "$HOME/.pi/agent/auth.json"
    "$HOME/.claude/auth.json"
  )
  for p in "${candidate_paths[@]}"; do
    [ -f "$p" ] || continue
    case "$provider" in
      openrouter) jq -r ".openrouter.key // empty" "$p" 2>/dev/null ;;
      opencode-go)
        case "$field" in
          apiKey)      jq -r '.["opencode-go"].key // empty' "$p" 2>/dev/null ;;
          workspaceId) jq -r '.providerQuota.opencodeGo.workspaceId // empty' "$p" 2>/dev/null ;;
          authCookie)  jq -r '.providerQuota.opencodeGo.authCookie  // empty' "$p" 2>/dev/null ;;
        esac ;;
      minimax) jq -r '.minimax.key // empty' "$p" 2>/dev/null ;;
    esac && return 0
  done
}

# Resolve a config value: config file → env → fallback auth.
# Uses bracket notation for provider keys with dashes (e.g. "opencode-go").
resolve() {
  local provider="$1" field="$2" envname="$3"
  local v
  v="$(config_get ".[\"$provider\"].$field")"
  [ -n "$v" ] && { printf '%s' "$v"; return; }
  v="${!envname:-}"
  [ -n "$v" ] && { printf '%s' "$v"; return; }
  fallback_auth "$provider" "$field"
}
