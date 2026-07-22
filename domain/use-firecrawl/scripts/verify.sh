#!/usr/bin/env bash
# verify.sh — ad-hoc verification for use-firecrawl skill (v2.0)
# Validates the Firecrawl stack AND the harness wiring.
# Copy to a mktemp path, execute, delete after.
#
# Usage:
#   SCRIPT=$(mktemp -t hermes-verify-firecrawl-XXXXXX.sh)
#   cp <skill-dir>/scripts/verify.sh "$SCRIPT"
#   bash "$SCRIPT" /path/to/firecrawl-local
#   rm -f "$SCRIPT"
set -u
PASS=0; FAIL=0
ok() { PASS=$((PASS+1)); printf "  \033[32m✓\033[0m %s\n" "$1"; }
ko() { FAIL=$((FAIL+1)); printf "  \033[31m✗\033[0m %s\n" "$1"; }

FC_DIR="${1:-$HOME/Documents/Projects/firecrawl-local}"
API="http://localhost:3002"
KEY="fc-local-dev-key"

echo "── V1: .env source-of-truth"
[ -f "$FC_DIR/.env" ] && ok ".env exists" || { ko ".env missing"; exit 1; }
grep -q "^MODEL_EMBEDDING_NAME=qwen/qwen3-embedding-8b" "$FC_DIR/.env" \
  && ok "MODEL_EMBEDDING_NAME=qwen/qwen3-embedding-8b" || ko "MODEL_EMBEDDING_NAME wrong"
grep -q "^MODEL_NAME=deepseek/deepseek-v4-pro" "$FC_DIR/.env" \
  && ok "MODEL_NAME=deepseek/deepseek-v4-pro" || ko "MODEL_NAME wrong"
grep -q "^OPENAI_BASE_URL=https://openrouter.ai/api/v1" "$FC_DIR/.env" \
  && ok "OPENAI_BASE_URL -> OpenRouter" || ko "OPENAI_BASE_URL wrong"
if grep -qE "^OPENROUTER_API_KEY=sk-or-v1-" "$FC_DIR/.env"; then
  ok "OPENROUTER_API_KEY has real value"
else
  ko "OPENROUTER_API_KEY missing or placeholder"
fi
grep -q "^\.env$" "$FC_DIR/.gitignore" 2>/dev/null \
  && ok ".env in .gitignore" || ko ".env NOT in .gitignore"

echo ""
echo "── V2: docker compose config propagates"
RENDER=$(docker compose --env-file "$FC_DIR/.env" -f "$FC_DIR/docker-compose.yaml" -f "$FC_DIR/docker-compose.override.yaml" config 2>/dev/null)
[ -n "$RENDER" ] && ok "compose config renders" || ko "compose config failed"
echo "$RENDER" | grep -q "MODEL_EMBEDDING_NAME: qwen/qwen3-embedding-8b" && ok "MODEL_EMBEDDING_NAME in compose" || ko "MODEL_EMBEDDING_NAME not in compose"
echo "$RENDER" | grep -q "OPENAI_BASE_URL: https://openrouter.ai/api/v1" && ok "OPENAI_BASE_URL in compose" || ko "OPENAI_BASE_URL not in compose"
echo "$RENDER" | grep -q 'mem_limit: "4294967296"' && ok "api mem_limit = 4GiB (override applied)" || ko "api override not applied"

echo ""
echo "── V3: 6/6 containers alive"
for c in firecrawl-api-1 firecrawl-nuq-postgres-1 firecrawl-rabbitmq-1 firecrawl-redis-1 firecrawl-playwright-service-1 firecrawl-foundationdb-1; do
  STATE=$(docker ps --format '{{.Names}} {{.Status}}' | grep "^$c " || true)
  [ -n "$STATE" ] && ok "$c : $(echo $STATE | cut -d' ' -f2-)" || ko "$c MISSING"
done

echo ""
echo "── V4: scrape markdown (no-LLM baseline)"
T0=$(python3 -c "import time;print(time.time())")
HTTP=$(curl -sS --max-time 15 -o /tmp/_hv_f1.json -w "%{http_code}" -X POST "$API/v2/scrape" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $KEY" \
  -d '{"url":"https://example.com","formats":["markdown"]}')
T1=$(python3 -c "import time;print(time.time())")
EL=$(python3 -c "print(f'{$T1-$T0:.2f}')")
[ "$HTTP" = "200" ] && ok "POST /v2/scrape -> 200 in ${EL}s" || ko "scrape HTTP $HTTP"
python3 -c "import json; d=json.load(open('/tmp/_hv_f1.json')); assert d['success'] and d['data']['metadata']['title']=='Example Domain'" 2>/dev/null \
  && ok "title=Example Domain" || ko "title mismatch"

echo ""
echo "── V5: LLM JSON extraction (validates OpenRouter + Deepseek)"
T0=$(python3 -c "import time;print(time.time())")
HTTP=$(curl -sS --max-time 60 -o /tmp/_hv_f2.json -w "%{http_code}" -X POST "$API/v2/scrape" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $KEY" \
  -d '{"url":"https://example.com","formats":["markdown",{"type":"json","prompt":"Return a JSON object with: title (string), purpose (one sentence), isIana (boolean)"}]}')
T1=$(python3 -c "import time;print(time.time())")
EL=$(python3 -c "print(f'{$T1-$T0:.2f}')")
[ "$HTTP" = "200" ] && ok "LLM scrape -> 200 in ${EL}s" || ko "LLM scrape HTTP $HTTP"
python3 -c "import json; d=json.load(open('/tmp/_hv_f2.json')); assert d['success'] and d['data'].get('json') and d['data']['json'].get('title')" 2>/dev/null \
  && ok "JSON extraction returned non-empty title" || ko "JSON extraction empty"
[ "${EL%.*}" -ge 3 ] && ok "LLM latency >=3s (model call evident)" || ko "LLM latency ${EL}s too fast"

echo ""
echo "── V6: /v2/search (embedding path)"
T0=$(python3 -c "import time;print(time.time())")
HTTP=$(curl -sS --max-time 60 -o /tmp/_hv_f3.json -w "%{http_code}" -X POST "$API/v2/search" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $KEY" \
  -d '{"query":"python web scraping library","limit":3}')
T1=$(python3 -c "import time;print(time.time())")
EL=$(python3 -c "print(f'{$T1-$T0:.2f}')")
[ "$HTTP" = "200" ] && ok "/v2/search -> 200 in ${EL}s" || ko "search HTTP $HTTP"
python3 -c "import json; d=json.load(open('/tmp/_hv_f3.json')); assert d['success'] and len(d['data']['web'])>=1" 2>/dev/null \
  && ok "search returned >=1 ranked result" || ko "search returned no results"
[ "${EL%.*}" -ge 1 ] && ok "search latency >=1s (embedding call evident)" || ko "search latency too fast"

echo ""
echo "── V7: harness wiring detected"
# Detect which harness is configured
HARNESS_WIRED=""
# Hermes
if [ -f "$HOME/.hermes/.env" ] && grep -q "^FIRECRAWL_API_URL=http://localhost:3002" "$HOME/.hermes/.env" 2>/dev/null; then
  ok "Hermes: FIRECRAWL_API_URL wired in ~/.hermes/.env"
  HARNESS_WIRED="hermes"
fi
# Pi
if grep -q "FIRECRAWL_API_URL=http://localhost:3002" "$HOME/.zshrc" "$HOME/.bashrc" 2>/dev/null; then
  ok "Pi: FIRECRAWL_API_URL exported in shell RC"
  HARNESS_WIRED="${HARNESS_WIRED:+$HARNESS_WIRED+}pi"
fi
# OpenCode
if [ -f "$HOME/.config/opencode/config.json" ] && grep -q "FIRECRAWL_API_URL" "$HOME/.config/opencode/config.json" 2>/dev/null; then
  ok "OpenCode: FIRECRAWL_API_URL in MCP config"
  HARNESS_WIRED="${HARNESS_WIRED:+$HARNESS_WIRED+}opencode"
fi
# Generic
if [ -z "$HARNESS_WIRED" ]; then
  echo "  (no harness wiring detected yet — step 9 may not have run)"
fi

rm -f /tmp/_hv_f1.json /tmp/_hv_f2.json /tmp/_hv_f3.json
echo ""
echo "── Summary: $PASS pass · $FAIL fail"
[ $FAIL -eq 0 ] && exit 0 || exit 1
