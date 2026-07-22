---
name: context7-live-docs
description: |
  Fetch live, snippet-level docs of fast-moving open-source repos via the
  Context7 API. Prefer over parametric knowledge when the answer depends on
  a specific library version, before cloning a heavy monorepo, or when a
  build decision rests on the current shape of a rapidly-iterated API
  (Firecrawl, LangChain, Next.js, Vite, etc.).
  Use when about to git-clone a heavy monorepo, when training-cutoff knowledge
  of a recent library version is uncertain, or when the user names Context7 /
  ctx7 / "live docs" / "fresh docs".
invocation: auto
layer: utility
language: en-US
metadata:
  version: "1.1.0"
---

# context7-live-docs — live repo docs via Context7

Parametric knowledge of large open-source repos goes stale fast. Context7
indexes them as snippets and serves them via a free REST API. Hit it BEFORE
`git clone` on a heavy monorepo and BEFORE trusting the training cutoff.

This skill uses the **`ctx7` CLI** (official, npm: `ctx7@0.5.5+`, bin
`ctx7`) as the primary backend. Fallback to `curl` against the REST API if
the CLI is missing. Triangulate with raw GitHub + a compose/YAML pre-flight
for any high-stakes build decision.

## When (self-trigger)

- About to `git clone` a heavy monorepo (Next.js, Turborepo, LangChain, etc.)
  to read its docs.
- Question depends on a *specific* version of a fast-moving repo:
  - "Does Firecrawl v2 still support `OPENAI_BASE_URL` for self-host?"
  - "What env vars does Vite 6 expose for SSR?"
  - "LangChain JS: did `createAgent` ship or is it still `createReactAgent`?"
- Build decision rests on the current shape of a rapidly-iterated API.
- User names `context7`, `ctx7`, "live docs", "fresh docs", "current docs".

## What it does

1. **Resolve library name → Context7 ID** via `ctx7 library`.
2. **Pull snippets for a topic** via `ctx7 docs` — returns markdown with
   source URLs and `lastUpdate` timestamps.
3. **Triangulate** for high-stakes decisions: Context7 + raw GitHub
   `main` + `docker compose --env-file .env config` (or equivalent).
4. **Fail loud** when Context7 is silent, unverified, or stale.

The agent picks the cheapest layer first (Context7 snippets), escalates
only if trust signals are weak.

## Quick start (CLI)

```bash
# Install once: npm i -g ctx7
# Verify:       ctx7 --version       # expect 0.5.5+

# 1. Resolve a library name to its Context7 ID
ctx7 library firecrawl
# -> /firecrawl/firecrawl-docs

# 2. Pull docs for a topic
ctx7 docs /firecrawl/firecrawl-docs "self-host OPENAI_BASE_URL"
# -> markdown snippets, source URLs, lastUpdateDate inline
```

## API (fallback, no CLI)

Base: `https://context7.com/api/v1`

```bash
# 1. Search
curl -sSL "https://context7.com/api/v1/search?query=firecrawl+self-host" \
  | python3 -c "
import json, sys
for r in json.load(sys.stdin).get('results', [])[:5]:
    print(r['id'], '|', r.get('lastUpdateDate',''), '|', r.get('state',''))"

# 2. Snippets by topic
curl -sSL "https://context7.com/api/v1/<owner>/<repo>?type=txt&topic=<urlencoded-topic>"
```

Use the API fallback only when `ctx7` is missing or broken. Prefer the CLI
because it handles auth, pagination, and result formatting consistently.

## CLI ↔ API command map

| Action                  | CLI                          | API                                                                |
|-------------------------|------------------------------|--------------------------------------------------------------------|
| Search by name          | `ctx7 library <name>`        | `GET /search?query=<name>`                                         |
| Fetch by ID + topic     | `ctx7 docs <id> <query>`     | `GET /<owner>/<repo>?type=txt&topic=<query>`                       |
| Auth check              | `ctx7 whoami`                | n/a — API is anonymous for free tier                                |
| Self-update             | `ctx7 upgrade`               | n/a                                                                |

## Trust signals (read these before trusting the output)

| Signal             | Where to find it                | Green flag              |
|--------------------|---------------------------------|-------------------------|
| `state`            | `ctx7 library` output           | `"finalized"`           |
| `verified`         | `ctx7 library` output           | `true`                  |
| `trustScore`       | `ctx7 library` output           | `>= 8`                  |
| `lastUpdateDate`   | snippet header / library output | `< 12mo`                |

**Never trust a `state != "finalized"` or `verified: false` snippet for a
high-stakes decision.** Cross-check with the actual repo.

## Triangulated verification (Context7 + raw GitHub + compose pre-flight)

Context7 alone is **not enough** for a high-stakes build. Pair it with two
cheap, fast checks that catch what Context7 misses:

1. **Context7 (`ctx7 docs`)** — the *shape* of the config and the *names*
   of env vars. Fastest layer; indexes docs not necessarily the latest
   source. `lastUpdateDate > 12mo` → cross-check.
2. **GitHub raw** — the actual `docker-compose.yaml`, `Dockerfile`, or
   current `.env.example`. Use the `main` branch SHA, not tagged
   releases, unless you specifically need an old version.
   `curl -sSL https://raw.githubusercontent.com/<owner>/<repo>/main/<path>`
   is the move; **don't** re-derive file content from Context7 snippets.
3. **`docker compose config` pre-flight** — before any `up --build` (can
   take 5-10 min), run `docker compose --env-file .env config` to confirm:
   (a) YAML parses, (b) every env var expands, (c) override files apply.
   Catches the entire class of "I built the wrong image because of an
   env typo" errors before they cost a rebuild.

Worked example (Firecrawl self-host):

```bash
# 1. Context7: confirm OPENAI_BASE_URL is the OpenAI-compat override
ctx7 library firecrawl
ctx7 docs /firecrawl/firecrawl-docs "self-host OPENAI_BASE_URL"

# 2. GitHub raw: see the actual service graph
curl -sSL https://raw.githubusercontent.com/firecrawl/firecrawl/main/docker-compose.yaml

# 3. Compose pre-flight: confirm 7 services, env expands, override applies
docker compose --env-file .env config

# Then: docker compose up -d --build
```

## When Context7 lies or is silent

Three known classes of silent failure:

- **Embeddings on OpenRouter** — `/v1/models` does NOT list embedding
  models even though `google/gemini-embedding-2` exists. Confirm
  directly with `curl .../embeddings`; do not trust the models list.
- **Endpoint mismatches** — OpenAI-compatible providers expose either
  `/v1/chat/completions` (legacy) or `/v1/responses` (new). Most models
  on OpenRouter support both, but some only one. Fix is in the provider's
  model card, not Context7.
- **Deprecated endpoints** — some services return
  `{"success":true,"id":"...","replacement":"/v2/scrape"}` and tell you
  to use a newer path. Always grep the source for `deprecat` if a
  "natural" endpoint misbehaves.

## Pitfalls

- **Unverified repos can be AI summaries.** `verified: false` or
  `state != "finalized"` may have been generated, not scraped. Cross-check
  with the actual repo before committing to a finding.
- **Context7 doesn't replace the repo for code reading.** It indexes docs,
  not source. If you need to read implementation, you still need a clone —
  just a targeted one with `sparse-checkout` after Context7 tells you
  which paths matter.
- **Topic parameter is fuzzy, not exact.** "self-host" may return docs
  that mention it in passing. Read the source URL at the top of each
  snippet to confirm it's the doc you actually wanted.
- **Rate limits and quotas.** Free tier is generous for ad-hoc lookups;
  for batch research, dispatch subagents and have them each run their
  own `ctx7 docs` queries to stay under any per-IP caps.
- **`ctx7` is a young CLI (0.5.x).** Pin a known-good version in
  `package.json` if your harness runs scripted upgrades. Verify with
  `ctx7 --version` before each session that uses it.

## Setup (one-time, per machine)

```bash
# Install
npm install -g ctx7

# Verify
which ctx7 && ctx7 --version      # expect 0.5.5+

# Optional: authenticate for higher rate limits / private repos
ctx7 login

# Check
ctx7 whoami
```

If `npm i -g ctx7` fails (no Node.js, no write access to global prefix):

```bash
# Option A: npx shim (per-invocation, slower)
npx -y ctx7@latest docs <id> <query>

# Option B: API fallback
# Use the curl recipes in the "API (fallback, no CLI)" section above.
```

## Out of scope

- Full repo cloning (use `git clone` directly; `sparse-checkout` once
  Context7 tells you which paths matter).
- Web search across the open web (use `web_search` / `web_extract`).
- Academic paper search (use `research-literature`).

## Related

- `research` — invokes this as a primary-source oracle when external
  facts are needed before build.
- `api-credentials` — often used in conjunction; Context7 is the docs
  side, `api-credentials` is the keys side.

## Files in this umbrella

- `references/firecrawl-selfhost-workflow.md` — full recipe for spinning
  up a self-hosted Firecrawl instance with OpenRouter as the LLM
  provider. Includes the env-var override pattern,
  `docker-compose.override.yaml` for resource limits on a MacBook, the
  openrouter-embeddings gotcha, and the build/runtime timing budget.
  Use when the user asks for "Firecrawl local", "containerized web
  crawler", or any similar setup.
- `scripts/verify-firecrawl.sh` — runnable smoke test. Checks compose
  config, 6/6 containers alive, basic scrape, and (if the key is real)
  LLM extraction. Exit 0 = healthy. Use as a cron health check or
  post-deploy verification.
