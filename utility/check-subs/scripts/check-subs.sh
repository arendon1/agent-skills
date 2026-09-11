#!/usr/bin/env bash
# check-subs.sh — main entry point for the check-subs skill.
#
# Subcommands:
#   probe [provider]    — run probes (all 3 or just one); write state file
#   status [--human]    — read state file; pretty-print or JSON
#   record P W P S      — post-dispatch feedback: record reset for (provider, window, percent, resetEtaSec)
#   thresholds          — show the current threshold table
#   config              — show resolved config (file → env → fallback)
#
# See SKILL.md and references/ for full docs.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

# ---- subcommands ------------------------------------------------------------

cmd_probe() {
  local target="${1:-all}"
  ensure_state_dir
  local providers=(openrouter opencode-go minimax)
  case "$target" in
    all) ;;
    openrouter)  providers=(openrouter) ;;
    opencode-go|og) providers=(opencode-go) ;;
    minimax)     providers=(minimax) ;;
    *)
      log_error "unknown provider: $target"
      exit 64 ;;
  esac

  local now; now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  for p in "${providers[@]}"; do
    log_info "probing $p"
    local block=""
    case "$p" in
      openrouter)  block="$("$SCRIPT_DIR/providers/or.sh"      2>/dev/null || printf '{"status":"error"}')" ;;
      opencode-go) block="$("$SCRIPT_DIR/providers/og.sh"      2>/dev/null || printf '{"status":"error"}')" ;;
      minimax)     block="$("$SCRIPT_DIR/providers/minimax.sh" 2>/dev/null || printf '{"status":"error"}')" ;;
    esac
    state_merge_provider "$p" "$block"
  done

  # Print the resulting state.
  state_get '.' | jq '.'
}

cmd_status() {
  local human=0
  [ "${1:-}" = "--human" ] && human=1
  if [ ! -f "$STATE_FILE" ]; then
    log_warn "no state file at $STATE_FILE — run 'probe' first"
    exit 1
  fi
  if [ "$human" = "1" ]; then
    # Iterate over providers at the bash level so each provider gets a single
    # header, and nested .key doesn't shadow the provider name.
    jq -r '.providers | keys[]' "$STATE_FILE" | while read -r p; do
      jq -r --arg p "$p" '
        .providers[$p] as $pv |
        "[" + $p + "] " + ($pv.status // "?") + "\n" +
        (if $pv.credits then
          "  usage_monthly:  " + (($pv.credits.usage_monthly // "?") | tostring) + "\n" +
          "  usage_weekly:   " + (($pv.credits.usage_weekly  // "?") | tostring) + "\n" +
          "  limit_remaining: " + (($pv.credits.limit_remaining // "n/a") | tostring) + "\n"
        else "" end) +
        (if $pv.windows then
          # Flat shape: key is window name like "5h" / "weekly" / "monthly"
          (
            [
              $pv.windows | to_entries[] |
              "  " + .key + ":  " + (.value.consumedPercent|tostring) + "% consumed, resets in " + ((.value.resetEtaMs // 0) / 1000 | tostring) + "s\n"
            ] | join("")
          )
        else "" end) +
        (if $pv.liveness then
          "  liveness: " + (($pv.liveness.alive // false) | tostring) + " (last ok: " + ($pv.liveness.last_ok // "?") + ")\n"
        else "" end) +
        "  next probe: " + ($pv.next_probe_at // "?") + "\n"
      ' "$STATE_FILE"
    done
  else
    jq '.' "$STATE_FILE"
  fi
}

cmd_record() {
  local provider="$1" window="$2" pct="$3" reset_eta_sec="$4"
  [ -z "$provider" ] || [ -z "$window" ] || [ -z "$pct" ] || [ -z "$reset_eta_sec" ] && {
    log_error "usage: record <provider> <window> <consumedPercent> <resetEtaSec>"
    exit 64
  }
  ensure_state_dir
  local now epoch; now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  epoch=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$now" +%s 2>/dev/null \
        || date -u -d "$now" +%s)
  local next_at; next_at=$(date -u -r $((epoch + reset_eta_sec)) +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
                       || date -u -d "@$((epoch + reset_eta_sec))" +%Y-%m-%dT%H:%M:%SZ)

  # Update the window block in place (flat shape: key is the window name).
  local current; current="$(state_get '.')"
  echo "$current" | jq --arg p "$provider" --arg w "$window" --argjson pct "$pct" \
                       --arg next "$next_at" --arg now "$now" '
    .providers[$p].windows[$w] = {
      key: $w,
      consumedPercent: $pct,
      resetEtaMs: '$((reset_eta_sec * 1000))',
      resetAt: $next,
      status: "exhausted"
    }
    | .providers[$p].next_probe_at = $next
    | .providers[$p].status = "ok"
    | .updated_at = $now
  ' > "$STATE_FILE.tmp.$$"
  mv -f "$STATE_FILE.tmp.$$" "$STATE_FILE"
  log_info "recorded $provider/$window exhausted ($pct%), next probe at $next_at"
}

cmd_thresholds() {
  printf '%s\n' 'window  warn  danger'
  printf '%s\n' '------  ----  ------'
  for w in 5h weekly monthly; do
    printf '%-6s  %3d   %3d\n' "$w" "$(get_warn "$w")" "$(get_danger "$w")"
  done
}

cmd_config() {
  printf 'config file: %s\n' "$CONFIG_FILE"
  printf 'state file:  %s\n' "$STATE_FILE"
  printf '\nresolved values:\n'
  printf '  openrouter.apiKey:      %s\n' "$(mask_key "$(resolve openrouter apiKey OPENROUTER_API_KEY)")"
  printf '  opencode-go.workspaceId:%s\n' "$(resolve opencode-go workspaceId OPENCODE_GO_WORKSPACE_ID)"
  printf '  opencode-go.authCookie: %s\n' "$(mask_key "$(resolve opencode-go authCookie OPENCODE_GO_AUTH_COOKIE)")"
  printf '  minimax.apiKey:         %s\n' "$(mask_key "$(resolve minimax apiKey MINIMAX_API_KEY)")"
}

cmd_watch() {
  # Refresh interval (seconds). Default 30. Honors CHECK_SUBS_WATCH_INTERVAL.
  local interval="${CHECK_SUBS_WATCH_INTERVAL:-30}"
  [ $# -gt 0 ] && interval="$1"

  # ANSI: clear screen, move cursor home, hide cursor.
  printf '\033[2J\033[?25l'

  # Cleanup on exit — restore cursor.
  trap 'printf "\033[?25h\n"; exit 0' INT TERM EXIT

  while true; do
    {
      printf '\033[H'  # home
      printf 'check-subs watch — refresh every %ss (Ctrl-C to quit)\n' "$interval"
      printf 'updated: %s   state: %s\n\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$STATE_FILE"

      # Probe (silent: probe prints to stderr only)
      "$SCRIPT_DIR/check-subs.sh" probe all >/dev/null 2>&1 || true

      # Render human status
      "$SCRIPT_DIR/check-subs.sh" status --human 2>/dev/null

      # Footer with useful at-a-glance info
      printf '\n'
      if [ -f "$STATE_FILE" ]; then
        jq -r '
          .providers | to_entries[] |
          select(.value.status == "ok") |
          (
            if .key == "opencode-go" then
              "  [og]        5h=" + (.value.windows["5h"].consumedPercent // "?" | tostring) + "%  weekly=" + (.value.windows.weekly.consumedPercent // "?" | tostring) + "%  monthly=" + (.value.windows.monthly.consumedPercent // "?" | tostring) + "%"
            elif .key == "minimax" then
              "  [minimax]   5h=" + (.value.windows["5h"].consumedPercent // "?" | tostring) + "%  weekly=" + (.value.windows.weekly.consumedPercent // "?" | tostring) + "%"
            elif .key == "openrouter" then
              "  [or]        usage_monthly=$" + (.value.credits.usage_monthly // "?" | tostring)
            else empty end
          )
        ' "$STATE_FILE" 2>/dev/null
        printf '  [thresholds] 5h: warn@70%% danger@85%% | weekly: warn@75%% danger@90%%\n'
      fi
    } || true

    sleep "$interval"
  done
}

# ---- entry -----------------------------------------------------------------

usage() {
  cat <<EOF
check-subs — subscription liveness + quota probe

USAGE:
  check-subs probe [provider]    probe all 3 (or one) and write state
  check-subs status [--human]    show current state
  check-subs watch [interval]    live TUI: probe + status loop every Ns (default 30)
  check-subs record P W P S      record post-dispatch reset (provider window pct etaSec)
  check-subs thresholds          show threshold table
  check-subs config              show resolved config (masked keys)

ENV:
  CHECK_SUBS_WATCH_INTERVAL      default watch interval (seconds, default 30)

PROVIDERS: openrouter, opencode-go, minimax

STATE:   $STATE_FILE
CONFIG:  $CONFIG_FILE
EOF
}

main() {
  [ $# -lt 1 ] && { usage; exit 64; }
  local cmd="$1"; shift
  case "$cmd" in
    probe)      cmd_probe "$@" ;;
    status)     cmd_status "$@" ;;
    watch)      cmd_watch "$@" ;;
    record)     cmd_record "$@" ;;
    thresholds) cmd_thresholds ;;
    config)     cmd_config ;;
    -h|--help|help) usage ;;
    *) log_error "unknown subcommand: $cmd"; usage; exit 64 ;;
  esac
}

main "$@"
