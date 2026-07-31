#!/usr/bin/env bash
# providers/og.sh — probe opencode-go Go subscription quota.
#
# Endpoint: GET https://opencode.ai/workspace/{workspaceId}/go
# Auth:     Cookie: auth=<authCookie>  (NOT an API key — OAuth session)
# Response: SSR HTML with embedded {rollingUsage,weeklyUsage,monthlyUsage} props.
#
# Reuses the regex pattern from slkiser/opencode-quota v4.4.0.
# Each prop is a tuple: {status:"ok",resetInSec:N,usagePercent:N}.
#
# Outputs a JSON block on stdout (or "null" on error).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib.sh
source "$SCRIPT_DIR/../lib.sh"

# Map OG's prop names to our canonical window keys (function — bash 3.2 has no assoc arrays).
og_prop_to_key() {
  case "$1" in
    rollingUsage) echo 5h ;;
    weeklyUsage)  echo weekly ;;
    monthlyUsage) echo monthly ;;
    *) return 1 ;;
  esac
}

USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Gecko/20100101 Firefox/148.0'

probe() {
  local ws; ws="$(resolve opencode-go workspaceId OPENCODE_GO_WORKSPACE_ID)"
  local cookie; cookie="$(resolve opencode-go authCookie OPENCODE_GO_AUTH_COOKIE)"
  if [ -z "$ws" ] || [ -z "$cookie" ]; then
    log_warn "og: workspaceId or authCookie not configured"
    printf '%s' '{"status":"not-configured","api":"GET /workspace/{id}/go (HTML scrape)"}'
    return 0
  fi

  local resp http_code
  # Cookie name is "auth" — prepend it if not already present.
  local cookie_header="auth=${cookie#auth=}"
  resp="$(curl -sS --max-time 10 -L -w '\n%{http_code}' \
    -H "User-Agent: $USER_AGENT" \
    -H "Accept: text/html" \
    -H "Cookie: $cookie_header" \
    "https://opencode.ai/workspace/$ws/go" 2>/dev/null)" || {
      log_warn "og: network error"
      printf '%s' '{"status":"network-error","api":"GET /workspace/{id}/go (HTML scrape)"}'
      return 0
    }
  http_code="$(printf '%s' "$resp" | tail -1)"
  resp="$(printf '%s' "$resp" | sed '$d')"

  if [ "$http_code" != "200" ]; then
    log_warn "og: HTTP $http_code"
    printf '%s' "{\"status\":\"auth-error\",\"api\":\"GET /workspace/{id}/go (HTML scrape)\",\"http_code\":$http_code}"
    return 0
  fi

  # Parse with awk — the SSR HTML is single-line, regex matches inline.
  # Captures: propName, status, resetInSec, usagePercent.
  # Output: JSON object { "<window>": {key, consumedPercent, resetEtaMs, status}, ... }
  local parsed
  parsed="$(printf '%s' "$resp" | perl -ne '
    BEGIN { %map = ("rollingUsage","5h","weeklyUsage","weekly","monthlyUsage","monthly"); }
    while (m{(rollingUsage|weeklyUsage|monthlyUsage):\$R\[\d+\]=\{status:"([^"]+)",resetInSec:(\d+),usagePercent:(\d+)\}}g) {
      my ($prop, $st, $reset, $pct) = ($1, $2, $3, $4);
      my $key = $map{$prop};
      next unless defined $key;
      next if $st ne "ok";
      next if $pct !~ /^\d+$/ || $pct < 0;
      $reset_ms = $reset * 1000;
      $windows{$key} = qq({"key":"$key","consumedPercent":$pct,"resetEtaMs":$reset_ms,"status":"$st"});
    }
    END {
      print "{" if %windows;
      my $first = 1;
      for my $k (sort keys %windows) {
        print "," unless $first; $first = 0;
        print "\"$k\":" . $windows{$k};
      }
      print "}";
    }
  ' 2>/dev/null)" || parsed=""

  if [ -z "$parsed" ] || [ "$parsed" = "{}" ]; then
    log_warn "og: parse error (no usage data extracted)"
    printf '%s' '{"status":"auth-error","api":"GET /workspace/{id}/go (HTML scrape)","comment":"no usage data parsed — cookie likely expired"}'
    return 0
  fi

  jq -c --argjson w "$parsed" '{
    status: "ok",
    api: "GET /workspace/{id}/go (HTML scrape)",
    kind: "subscription",
    windows: $w
  }' <<<'null' 2>/dev/null || {
    log_warn "og: jq wrap error"
    printf '%s' '{"status":"parse-error","api":"GET /workspace/{id}/go (HTML scrape)"}'
  }
}

probe
