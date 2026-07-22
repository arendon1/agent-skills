# Firecrawl self-hosted with OpenRouter LLM — full recipe

Session-captured workflow for spinning up a containerized Firecrawl
instance pointed at OpenRouter for the LLM provider, with all the
surprises and dead-ends included. Use this as a reference when the
user asks to self-host Firecrawl, scrape-the-web services more
generally, or any "containerized service with custom LLM provider"
setup.

Last verified: 2026-07-21 on macOS with OrbStack, 24GB RAM.

## Why this matters

The user's exact ask was: "spin a fully local (except for the LLM
which I want it to be from OpenRouter) containerized FIRECRAWL
instance to give you web crawling abilities." This is the recipe
that delivered it.

## Repo + architecture

- **Repo:** `https://github.com/firecrawl/firecrawl` (clone with
  `git clone --depth 1`)
- **Stack (from `docker-compose.yaml`):** 7 services
  - `api` (Node 22, 4 CPU / 8GB by default)
  - `playwright-service` (TypeScript, 2 CPU / 4GB)
  - `redis` (queue + rate limit)
  - `rabbitmq` (job queue, requires healthy check)
  - `nuq-postgres` (postgres 17, queue backend)
  - `foundationdb` + `foundationdb-init` (experimental queue
    backend, not used by default)
  - ports: 3002 (api), 6379 (redis), 5672 (rabbitmq), 15672
    (rabbitmq mgmt UI), 5432 (postgres)

## Env vars that matter for the LLM provider override

`docker-compose.yaml` reads these from the env / `.env`:

```env
# OpenAI-compatible override (Firecrawl uses the openai SDK + ai SDK
# under the hood; setting OPENAI_BASE_URL to an OpenAI-compatible
# endpoint swaps the provider)
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=<model-id-on-provider>
MODEL_EMBEDDING_NAME=<embedding-model-id-or-empty>
```

Firecrawl calls `/v1/responses` (not `/v1/chat/completions`).
OpenRouter supports both, but the model must accept the Responses
API format.

## Resource override pattern (MacBook-friendly)

Create `docker-compose.override.yaml` next to the main compose file
(Compose v2 picks it up automatically). Reduce the `api` and
`playwright-service` limits:

```yaml
services:
  api:
    cpus: "2.0"
    mem_limit: 4G
    memswap_limit: 4G
  playwright-service:
    cpus: "1.0"
    mem_limit: 2G
    memswap_limit: 2G
  rabbitmq:
    mem_limit: 1G
    cpus: "0.5"
```

Total: ~3GB RAM. Leaves 18GB+ on a 24GB Mac for the rest of the
system. Production defaults (8GB + 4GB + 1GB+) are oversized for
dev.

## Pre-flight gate (saves 5-10 min of rebuild)

Before any `up -d --build`:

```bash
cd /path/to/firecrawl-local
docker compose --env-file .env config \
  | grep -E "OPENAI_API_KEY|OPENAI_BASE_URL|MODEL_NAME|mem_limit"
```

If the env var expansion shows your key value (not the placeholder),
the YAML parses, and the override file's `mem_limit` shows up, you're
clear to launch.

## Build + start

```bash
# First time: ~5 min for image builds on OrbStack
docker compose --env-file .env up -d --build

# After edits to .env (e.g. paste the real OpenRouter key):
docker compose --env-file .env up -d --force-recreate --no-deps api
```

The `--no-deps api` flag is key — it restarts only the API
container so it reads the new env, without rebuilding anything.

## Smoke tests

```bash
# V1: scrape basic (no LLM, should work even with placeholder key)
curl -X POST http://localhost:3002/v2/scrape \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TEST_API_KEY}" \
  -d '{"url":"https://example.com","formats":["markdown"]}'

# V2: scrape with jsonOptions (REQUIRES LLM, fails with placeholder key)
curl -X POST http://localhost:3002/v2/scrape \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TEST_API_KEY}" \
  -d '{"url":"https://example.com","formats":["markdown",{"type":"json","prompt":"Return title, purpose, isIana"}]}'
```

V2 is the integration test: it confirms the LLM is being called
end-to-end and that the response includes a `data.json` field with
the structured extraction.

## Surprises / dead-ends

### 1. OpenRouter has no embeddings in `/v1/models`

`curl https://openrouter.ai/api/v1/models` returns 342 models, none
with "embed" in the id. The model `google/gemini-embedding-2`
exists at `openrouter.ai/google/gemini-embedding-2` but is not
exposed to the API list. This means: a service that does a
`GET /v1/models` to validate embedding models will not see it.

**For Firecrawl: this is fine.** Scrape, crawl, and JSON extraction
all work without embeddings. Only the smart-scrape and search
ranking features would benefit, and they degrade gracefully when
`MODEL_EMBEDDING_NAME` is unset.

**For other services that *require* embeddings:** use Ollama local
with `nomic-embed-text` (Firecrawl supports it via
`OLLAMA_BASE_URL` env var; other services may need a different
setup).

### 2. `BULL_AUTH_KEY is not set` warning

Cosmetic. Disables admin routes (Bull-Board UI for queue inspection).
Set it to any non-empty string if you want to inspect queues via
the web UI. Not blocking for normal scrape/crawl.

### 3. RabbitMQ "Cannot get a message from queue" error

The error `nproc` not found appears in Mac/ARM-Linux because
RabbitMQ tries to use `nproc` (Unix System V tool) and falls back.
Firecrawl catches the failure and falls back to postgres for the
queue. No fix needed, but the log is noisy.

### 4. `/v2/extract` is deprecated

It returns a 200 with `{"replacement":"/v2/scrape"}` and a warning.
Use `POST /v2/scrape` with `formats: ["markdown", {type: "json",
prompt: ...}]` instead. The old API surface is kept for
backward compat but every call is a no-op redirect.

### 5. `sparse-checkout` + filter=blob:none fights itself

When the goal is to read a few files from a large repo, the
natural instinct is `git clone --depth 1 --filter=blob:none
--sparse`. Firecrawl's repo has 200MB+ of submodules, nested
workspaces, and pnpm stores that break the sparse path. The
workaround that works:

- Use `git clone --depth 1` (full, shallow) — only ~80MB
- Use `git sparse-checkout` *without* `--filter=blob:none` if you
  need partial checkout
- Or just `git clone --depth 1` and read with `read_file` /
  `search_files` — fast enough for any single directory

## Verification script template

For ongoing health checks, the pattern is:

```bash
# 1. compose parses
RENDER=$(docker compose --env-file .env config 2>/dev/null)
echo "$RENDER" | grep -q "OPENAI_BASE_URL: https://openrouter.ai/api/v1"

# 2. 6/6 containers alive (skip foundationdb-init, one-shot)
for c in firecrawl-api-1 firecrawl-nuq-postgres-1 firecrawl-rabbitmq-1 \
         firecrawl-redis-1 firecrawl-playwright-service-1 firecrawl-foundationdb-1; do
  docker ps --format '{{.Names}} {{.Status}}' | grep "^$c "
done

# 3. scrape basic (no LLM)
curl -X POST http://localhost:3002/v2/scrape \
  -H "Authorization: Bearer ${TEST_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","formats":["markdown"]}'

# 4. LLM extraction (only if key is real, not placeholder)
```

See `../scripts/verify-firecrawl.sh` for the runnable version with
all checks in one place.

## Time budget

Realistic timing for first run on a clean Mac (24GB, OrbStack):

- `git clone --depth 1`: 30-60s
- `docker compose up -d --build`: 5-8 min (Rust compilation in API
  Dockerfile, Playwright Chromium download 180MB)
- API warm-up + first request: 30-60s
- Total: 7-10 min

After that, restarts (e.g. new env var) take 15-30s for the API
container alone.

## What works without LLM

If the user has no OpenRouter key (or it expires), the following
Firecrawl features still work end-to-end:

- `scrape` with `formats: ["markdown", "html", "links", "screenshot"]`
- `crawl` (uses scrape in a loop, no LLM call per page)
- `map` (sitemap/URL discovery)
- `batchScrape`

What does NOT work without LLM:

- `jsonOptions` with `prompt:` (calls LLM to extract per schema)
- `jsonOptions` with `schema:` (calls LLM to fill the schema)
- `summary` format
- `agent` API
- `llms.txt` generation
