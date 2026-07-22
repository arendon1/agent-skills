---
name: use-firecrawl
description: >-
  Spin a fully local containerized Firecrawl instance wired to OpenRouter for
  LLM + embeddings, verify Docker can mount it, and wire it to whatever harness
  the agent is running in (Hermes, Pi, OpenCode, or generic).
  Use when the user says "spin a local Firecrawl", "self-host Firecrawl",
  "give me web crawling", "set up web_search/web_extract locally", or wants
  crawling/scraping without paying Firecrawl SaaS. Defaults:
  deepseek/deepseek-v4-pro for LLM, qwen/qwen3-embedding-8b for embeddings —
  both via OpenRouter. Asks for the OpenRouter API key interactively. Detects
  the harness and writes the wiring to the right place.
invocation: auto
layer: domain
provides: [firecrawl-selfhost, web-crawling, web-scraping]
language: en-US
metadata:
  version: "2.0.0"
  risk_tier: MEDIUM
---

# Use Firecrawl (self-hosted, OpenRouter-backed, any harness)

Stand up a local Firecrawl instance in Docker, wire its LLM + embeddings to
OpenRouter (not OpenAI), verify Docker can mount everything before committing,
and connect the result to whatever harness the agent is running in. Zero
recurring cost to Firecrawl cloud; you pay only OpenRouter per-token for LLM
features.

**Defaults (do not change unless the user asks):**

| Component | Model | Cost |
|---|---|---|
| LLM (JSON extraction, summary) | `deepseek/deepseek-v4-pro` | ~$0.14/M tokens |
| Embeddings (semantic search, changeTracking) | `qwen/qwen3-embedding-8b` | $0.01/M tokens |
| Provider endpoint | `https://openrouter.ai/api/v1` | OpenAI-compatible |

The user only provides their OpenRouter API key. Everything else is baked.

## When to use

- User says "spin a local Firecrawl", "self-host Firecrawl", "give me web
  crawling", "set up web_search locally", "replace Firecrawl cloud"
- User wants web crawling/scraping in any harness without paying Firecrawl SaaS
- User has Docker + an OpenRouter key and wants it wired

**Do NOT use for:**
- Firecrawl cloud (managed) — that's just an API key, no Docker
- General self-hosting of other tools — this is Firecrawl-specific
- A throwaway POC — use `spike` instead

## What the user needs before starting

1. **Docker** running (OrbStack, Docker Desktop, or colima). The skill
   verifies this in the preflight step — do not assume.
2. **An OpenRouter API key** — get one at `https://openrouter.ai/keys` (sign in
   with Google/GitHub, add credits, create key). Starts with `sk-or-v1-`.
3. **~5GB free RAM** for the containers (Mac 16GB min, 24GB comfortable).
4. **~10 min** for the first build (Rust + Playwright Chromium download).

If any are missing, tell the user honestly and stop — don't improvise.

## The plan (9 steps, in order)

```
1. ask-key → 2. detect-harness → 3. preflight → 4. clone → 5. env
                                                          ↓
9. wire-harness ← 8. verify ← 7. smoke ← 6. up ←─────────
```

### Step 1 — Ask for the OpenRouter key

Use `clarify` with a single open-ended question:

> "Pégame tu OpenRouter API key (la consigues en https://openrouter.ai/keys —
> empieza con `sk-or-v1-`). La voy a escribir en el `.env` del repo local, no
> la voy a commitear."

Do NOT proceed without a real key. If the user asks "donde consigo la key",
point them to `https://openrouter.ai/keys` and stop. Do not fabricate a key.

### Step 2 — Detect the harness

The skill must identify which harness it's running in to know where to write
the wiring (step 9). Detect in this order — first hit wins:

| Signal | Harness | Wiring target |
|---|---|---|
| `~/.hermes/.env` exists OR `HERMES_HOME` env var set | Desktop agent (Hermes) | `~/.hermes/.env` + restart desktop |
| `pi` command available OR `~/.pi/` dir exists | Coding agent extension (Pi) | Shell env + extension install |
| `~/.config/opencode/` dir exists OR `OPENCODE_CONFIG_DIR` set | MCP-based agent | MCP config JSON + restart |
| None of the above | Generic shell | Shell env vars in `~/.bashrc` / `~/.zshrc` |

Detection commands (run silently, don't spam the user):

```bash
test -f ~/.hermes/.env && echo "desktop-agent" || \
  (command -v pi >/dev/null 2>&1 || test -d ~/.pi) && echo "extension-agent" || \
  (test -d ~/.config/opencode || test -n "$OPENCODE_CONFIG_DIR") && echo "mcp-agent" || \
  echo "generic"
```

If multiple harnesses are detected (e.g. both Hermes and Pi installed), ask
the user which one to wire via `clarify`. Do not guess.

### Step 3 — Preflight: verify Docker can mount everything

Run these checks **before** cloning. A failure here saves a 10-min build.

```bash
# (a) Docker engine alive
docker ps >/dev/null 2>&1 && echo "docker: up" || echo "docker: DOWN — start OrbStack/Docker Desktop/colima"

# (b) Available RAM (need ~5GB free for 6 containers)
sysctl hw.memsize 2>/dev/null | awk '{print "RAM:", int($2/1024/1024/1024)"GB"}' || \
  free -h 2>/dev/null | awk '/^Mem:/{print "RAM:", $2}'

# (c) Port 3002 free
lsof -nP -iTCP:3002 -sTCP:LISTEN 2>/dev/null | head -2 || echo "port 3002: free"

# (d) Disk space (need ~2GB for images + build)
df -h . | awk 'NR==2{print "disk free:", $4}'

# (e) OpenRouter key reachable (validates the key format + provider up)
curl -sS --max-time 10 -o /dev/null -w "openrouter: HTTP %{http_code}\n" \
  "https://openrouter.ai/api/v1/models" 2>/dev/null || echo "openrouter: unreachable"
```

**Abort conditions** (tell the user honestly, don't try to fix):

| Failure | What to tell the user |
|---|---|
| Docker not running | "Start OrbStack / Docker Desktop / colima and run `docker ps` to confirm, then try again." |
| RAM < 8GB | "This needs ~5GB for containers. Your machine has <8GB. Close other apps or use a beefier host." |
| Port 3002 in use | "Port 3002 is taken by another process. Stop it or edit `PORT` in the `.env`." |
| OpenRouter unreachable | "Can't reach OpenRouter. Check your internet connection or the key validity." |

If all preflight checks pass, proceed to step 4.

### Step 4 — Clone the Firecrawl repo

```bash
INSTALL_DIR="${INSTALL_DIR:-$HOME/Documents/Projects/firecrawl-local}"
git clone --depth 1 https://github.com/firecrawl/firecrawl.git "$INSTALL_DIR"
```

- Use `--depth 1` (81MB, no history). Do NOT use sparse-checkout — the
  monorepo's `apps/api/Dockerfile` needs the full build context.
- If the directory already exists, ask the user: reuse or reclone? Don't
  `rm -rf` without confirmation.

### Step 5 — Write the `.env`

Copy `templates/dot-env.template` from this skill to `$INSTALL_DIR/.env`.
Replace `__OPENROUTER_KEY__` with the real key from step 1.

Key fields (do not change unless the user asks):

```bash
OPENROUTER_API_KEY=<user's real key>
OPENAI_API_KEY=${OPENROUTER_API_KEY}
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=deepseek/deepseek-v4-pro
MODEL_EMBEDDING_NAME=qwen/qwen3-embedding-8b
USE_DB_AUTHENTICATION=false
TEST_API_KEY=fc-local-dev-key
```

**Security check after writing:**
```bash
grep "^\.env$" "$INSTALL_DIR/.gitignore"   # must return ".env"
git -C "$INSTALL_DIR" status --short        # must NOT show .env
```

If `.env` is NOT in `.gitignore`, add it manually before proceeding.

### Step 6 — Write the Mac-friendly override

Copy `templates/docker-compose.override.yaml` from this skill to
`$INSTALL_DIR/`. This reduces the default resource requests (8GB api + 4GB
playwright) to MacBook-friendly values (4GB api + 2GB playwright).

Pre-flight validate (must pass before `up`):
```bash
cd "$INSTALL_DIR"
docker compose --env-file .env config --services
# expect 7 services: api, playwright-service, redis, rabbitmq, nuq-postgres, foundationdb, foundationdb-init
docker compose --env-file .env config | grep "MODEL_EMBEDDING_NAME"
# expect: MODEL_EMBEDDING_NAME: qwen/qwen3-embedding-8b
```

### Step 7 — `docker compose up -d --build` + smoke test

**First build: 5–10 min** (Rust toolchain + Playwright Chromium + Go shared
libs). Use background execution and poll manually — do NOT block the session
with a 600s foreground timeout.

```bash
cd "$INSTALL_DIR"
docker compose --env-file .env up -d --build
```

After build, `docker ps` should show 6 containers `Up` (foundationdb-init
exits after setup — correct, it's a one-shot). **Wait 30s** after `Up`
before probing — the api container builds its DI graph and connects workers.

**Smoke test — 3 tests, in order:**

Test 1 — No-LLM scrape (regression baseline, <1s):
```bash
curl -sS --max-time 15 -X POST "http://localhost:3002/v2/scrape" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fc-local-dev-key" \
  -d '{"url":"https://example.com","formats":["markdown"]}'
```

Test 2 — LLM JSON extraction (validates OpenRouter + Deepseek, 5–15s):
```bash
curl -sS --max-time 60 -X POST "http://localhost:3002/v2/scrape" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fc-local-dev-key" \
  -d '{"url":"https://example.com","formats":["markdown",{"type":"json","prompt":"Return a JSON object with: title (string), purpose (one sentence), isIana (boolean)"}]}'
```

Test 3 — Embedding search (validates Qwen3 embeddings, 2–5s):
```bash
curl -sS --max-time 60 -X POST "http://localhost:3002/v2/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fc-local-dev-key" \
  -d '{"query":"python web scraping library","limit":3}'
```

### Step 8 — Verify (formal evidence)

Copy `scripts/verify.sh` from this skill to a `mktemp -t
hermes-verify-firecrawl-XXXXXX.sh` path, execute, and delete after. The
script asserts 25 checks across 7 sections. A 25/0 pass is the evidence.

```bash
SCRIPT=$(mktemp -t hermes-verify-firecrawl-XXXXXX.sh)
cp <skill-dir>/scripts/verify.sh "$SCRIPT"
bash "$SCRIPT" "$INSTALL_DIR"
rm -f "$SCRIPT"
```

Report the pass/fail numbers to the user. If any fail, check the pitfalls
section below — most failures are env-var mismatches, not real bugs.

### Step 9 — Wire the harness (harness-specific)

This is the step that changes per harness. Use the detection from step 2.

The **universal contract** is two env vars:

| Env var | Value |
|---|---|
| `FIRECRAWL_API_URL` | `http://localhost:3002` |
| `FIRECRAWL_API_KEY` | `fc-local-dev-key` |

Every Firecrawl client (Hermes plugin, `pi-firecrawl`, `firecrawl-mcp`,
`firecrawl-py`) reads these two vars. What changes is **where** they go and
**how** the harness picks them up.

#### Desktop agent (Hermes)

```bash
# Append to ~/.hermes/.env
echo '' >> ~/.hermes/.env
echo '# Self-hosted Firecrawl' >> ~/.hermes/.env
echo 'FIRECRAWL_API_URL=http://localhost:3002' >> ~/.hermes/.env
echo 'FIRECRAWL_API_KEY=fc-local-dev-key' >> ~/.hermes/.env
```

**Restart:** Cmd-Q the desktop app → reopen. The plugin re-initializes on
boot. You CANNOT restart the desktop from inside it without killing the
session — tell the user honestly to do it manually.

**Verify post-restart:** trigger the web extract or web search tool in a
fresh chat. If it returns markdown / results, it's wired. If it says "Web
tools not configured", the env wasn't read — check the `.env` syntax.

#### Coding agent extension (Pi)

Uses the Firecrawl extension which reads the same env vars.

```bash
# 1. Install the extension (if not already installed)
pi install npm:pi-firecrawl

# 2. Set the env vars in the shell the agent launches from
# Add to ~/.zshrc or ~/.bashrc:
echo '' >> ~/.zshrc
echo '# Self-hosted Firecrawl' >> ~/.zshrc
echo 'export FIRECRAWL_API_URL=http://localhost:3002' >> ~/.zshrc
echo 'export FIRECRAWL_API_KEY=fc-local-dev-key' >> ~/.zshrc

# OR set the key inside the agent (persists across sessions):
# /firecrawl key fc-local-dev-key
```

**Restart:** restart the agent session (exit + relaunch). The extension
reads `FIRECRAWL_API_URL` from the environment on startup.

**Verify post-restart:** use the scrape tool inside the agent. If it returns
markdown, it's wired.

#### MCP-based agent

Uses an MCP server config. The `firecrawl-mcp` npm package reads
`FIRECRAWL_API_KEY` and `FIRECRAWL_API_URL` from its environment block.

```bash
# Read existing config (or start fresh)
CONFIG_FILE="$HOME/.config/opencode/config.json"
mkdir -p "$(dirname "$CONFIG_FILE")"

# Write the MCP block (merge if config already exists)
cat > "$CONFIG_FILE" << 'JSON'
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "firecrawl": {
      "type": "local",
      "command": ["npx", "-y", "firecrawl-mcp"],
      "environment": {
        "FIRECRAWL_API_KEY": "fc-local-dev-key",
        "FIRECRAWL_API_URL": "http://localhost:3002"
      }
    }
  }
}
JSON
```

**Restart:** restart the agent. Verify with `/mcp` — Firecrawl should be
listed as attached. Then ask the agent to scrape a URL.

#### Generic (shell env vars)

For any other harness that reads standard env vars:

```bash
SHELL_RC="$([ -f ~/.zshrc ] && echo ~/.zshrc || echo ~/.bashrc)"
echo '' >> "$SHELL_RC"
echo '# Self-hosted Firecrawl' >> "$SHELL_RC"
echo 'export FIRECRAWL_API_URL=http://localhost:3002' >> "$SHELL_RC"
echo 'export FIRECRAWL_API_KEY=fc-local-dev-key' >> "$SHELL_RC"
source "$SHELL_RC"
```

Tell the user to restart their agent/IDE so the new env vars are picked up.

## Operating the instance

```bash
# Start (after first build, ~10s)
cd ~/Documents/Projects/firecrawl-local && docker compose --env-file .env up -d

# Stop (keeps data)
docker compose down

# Stop + delete all data (nuclear — don't do this casually)
docker compose down -v

# View logs
docker compose logs -f api

# Restart only the api (after .env change, ~15s)
docker compose --env-file .env up -d --force-recreate --no-deps api
```

## What each feature costs (OpenRouter per-token)

| Feature | LLM call? | Embedding call? | ~Cost per call |
|---|---|---|---|
| `scrape` markdown only | No | No | $0 |
| `scrape` with `jsonOptions` | Yes | No | ~$0.001–0.01 |
| `search` | Maybe | Yes | ~$0.001 |
| `changeTracking` | No | Yes | ~$0.001 |
| `agent` (beta, may be gated) | Yes | Yes | ~$0.01 |

For 50 pages scraped with JSON extraction: ~$0.05–$0.50. Embeddings add
~$0.001. LLM dominates cost; embeddings are 1–2 orders of magnitude cheaper.

## Common pitfalls

1. **`docker ps` says `Up` but API doesn't respond.** The container is still
   warming up. Wait 30s and probe with `curl --max-time 5
   http://localhost:3002/`.

2. **LLM call returns 401 `Missing Authentication header`.** The `.env` was
   not re-read by the running container. Fix: `docker compose --env-file .env
   up -d --force-recreate --no-deps api` (not just `restart`).

3. **`/v2/agent` returns `Agent beta is not enabled`.** Product gate in
   self-hosted builds. Not fixable without upstream changes.

4. **`changeTracking` returns `warning: Comparing failed`.** First scrape has
   no baseline. Scrape the same URL twice — the second call will diff. Not
   an error.

5. **RabbitMQ logs show `Cannot get a message from queue ... noproc`.**
   `nproc` is a Unix System V tool missing on macOS. Firecrawl falls back to
   Postgres. Not blocking — ignore.

6. **OpenRouter `/v1/models` doesn't list embedding models.** OpenRouter has
   14 embedding models under a different filter. `qwen/qwen3-embedding-8b`
   is addressable even if not listed. Test the call, don't trust the listing.

7. **Sparse git clone fails on the monorepo.** Use full `--depth 1` clone
   (81MB). Don't be clever with sparse-checkout.

8. **`.env` not in `.gitignore`.** The upstream `.gitignore` should exclude
   it. If not, add it manually before any `git add`. Never commit the key.

9. **Hermes `web_search` still says "not configured" after wiring.** The
   desktop process has env vars baked in at boot. A chat reload is not
   enough — the app must be fully restarted (Cmd-Q + reopen).

10. **Extension agent doesn't pick up the Firecrawl URL.** The firecrawl
    extension reads `FIRECRAWL_API_URL` from the process environment, not from
    a config file. Make sure the env var is exported in the shell that launches
    the agent, not just in a subshell.

11. **MCP agent server not attaching.** Run the agent's doctor command to
    inspect MCP load errors. The `firecrawl-mcp` package needs Node.js 18+ and
    `npx` on the PATH.

## Verification checklist

- [ ] `.env` has real `OPENROUTER_API_KEY` (not placeholder)
- [ ] `.env` is in `.gitignore`, not tracked by git
- [ ] `docker compose --env-file .env config` renders `MODEL_EMBEDDING_NAME` and `OPENAI_BASE_URL`
- [ ] `docker-compose.override.yaml` applied (api 4G, playwright 2G)
- [ ] 6/6 containers `Up` (api, postgres, rabbitmq, redis, playwright, foundationdb)
- [ ] `POST /v2/scrape` markdown returns 200 + "Example Domain" in <1s
- [ ] `POST /v2/scrape` with `jsonOptions` returns non-empty JSON (LLM works)
- [ ] `POST /v2/search` returns ranked results in >1s (embeddings work)
- [ ] Verify script (ad-hoc) ran with 0 failures
- [ ] Harness detected and wiring written to the correct location
- [ ] User told to restart their harness and given a smoke-test command
