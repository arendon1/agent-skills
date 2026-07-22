#!/usr/bin/env bash
# verify-firecrawl.sh — health check for a self-hosted Firecrawl
# instance pointed at OpenRouter for LLM.
#
# Usage:  bash scripts/verify-firecrawl.sh [path-to-firecrawl-dir]
# Default: $HOME/Documents/Projects/firecrawl-local
#
# Returns 0 if all checks pass, 1 otherwise. Use as a cron health
# check or as a post-deploy smoke test.

set -u
FC_DIR="${1:-$HOME/Documents/Projects/firecrawl-local}"
TEST_API_KEY="${TEST_API_KEY:-fc-local-dev-key}"
PASS=0; FAIL=0; SKIP=0

ok()   { PASS=$((PASS+1)); printf "  \033[32m✓\033[0m %s\n" "$1"; }
ko()   { FAIL=$((FAIL+1)); printf "  \033[31m✗\033[0m %s\n" "$1"; }
skip() { SKIP=$((SKIP+1)); printf "  \033[33m○\033[0m %s (skipped: %s)\n" "$1" "$2"; }

cd "$FC_DIR" || { echo "firecrawl dir not found: $FC_DIR"; exit 1; }

echo "── V1: docker compose config renders"
RENDER=$(docker compose --env-file .env config 2>/dev/null)
[ -n "$RENDER" ] && ok "compose config renders" || ko "compose config failed"
echo "$RENDER" | grep -q "OPENAI_BASE_URL: https://openrouter.ai/api/v1" \
  && ok "OPENAI_BASE_URL -> OpenRouter" || ko "OPENAI_BASE_URL wrong"

echo "── V2: 6/6 containers alive"
for c in firecrawl-api-1 firecrawl-nuq-postgres-1 firecrawl-rabbitmq-1 \
         firecrawl-redis-1 firecrawl-playwright-service-1 firecrawl-foundationdb-1; do
  STATE=$(docker ps --format '{{.Names}} {{.Status}}' | grep "^$c " || true)
  [ -n "$STATE" ] && ok "$c : $(echo "$STATE" | cut -d' ' -f2-)" || ko "$c MISSING"
done

echo "── V3: scrape basic (no LLM)"
TMP=$(mktemp)
HTTP=$(curl -sS --max-time 15 -o "$TMP" -w "%{http_code}" \
  -X POST "http://localhost:3002/v2/scrape" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TEST_API_KEY}" \
  -d '{"url":"https://example.com","formats":["markdown"]}' 2>/dev/null)
[ "$HTTP" = "200" ] && ok "POST /v2/scrape -> 200" || ko "scrape HTTP $HTTP"
if [ "$HTTP" = "200" ] && [ -s "$TMP" ]; then
  TITLE=$(python3 -c "import json; print(json.load(open('$TMP'))['data']['metadata'].get('title',''))" 2>/dev/null)
  [ "$TITLE" = "Example Domain" ] && ok "title=Example Domain" || ko "title=$TITLE"
fi
rm -f "$TMP"

echo "── V4: LLM extraction (skipped if key is placeholder)"
KEY=$(grep "^OPENROUTER_API_KEY" "$FC_DIR/.env" | cut -d= -f2)
if [ -z "$KEY" ] || [ "$KEY" = "__PENDIENTE__" ] || [ "$KEY" = "PEGAR_TU_KEY_AQUI" ]; then
  skip "LLM extraction" "OPENROUTER_API_KEY not pasted"
else
  TMP=$(mktemp)
  HTTP=$(curl -sS --max-time 60 -o "$TMP" -w "%{http_code}" \
    -X POST "http://localhost:3002/v2/scrape" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TEST_API_KEY}" \
    -d '{"url":"https://example.com","formats":["markdown",{"type":"json","prompt":"Return a JSON with: title, purpose, isIana"}]}' 2>/dev/null)
  [ "$HTTP" = "200" ] && ok "LLM scrape -> 200" || ko "LLM scrape HTTP $HTTP"
  if [ "$HTTP" = "200" ] && [ -s "$TMP" ]; then
    HAS_JSON=$(python3 -c "import json; d=json.load(open('$TMP')); print('json' in d.get('data',{}) and bool(d['data']['json']))" 2>/dev/null)
    [ "$HAS_JSON" = "True" ] && ok "JSON extraction returned non-empty field" || ko "JSON extraction empty"
  fi
  rm -f "$TMP"
fi

echo ""
echo "── Summary: $PASS pass · $FAIL fail · $SKIP skipped"
[ $FAIL -eq 0 ] && exit 0 || exit 1
