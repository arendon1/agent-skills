---
name: get-docs
description: |
  Ground the active agent in the project's tech stack by fetching live
  documentation via the Context7 CLI (`ctx7`, REST API fallback) and
  materializing relevant snippets as markdown references under
  `docs/stack/<lib>/<topic>.md` in the active project. Run after the
  stack has stabilized (typically after `design` or `spec` chose a
  library) so the same docs don't get re-fetched on every session.
  Use when the user says "ground the stack", "materialize docs for X",
  "fetch docs for this project", or asks about a library the active
  project uses without a `docs/stack/<lib>/` folder yet.
invocation: auto
layer: utility
provides: [ctx7-cli, stack-grounding, docs-materializer]
language: en-US
metadata:
  version: "2.1.0"
  architecture_exception:
    rule: AGENTS.md §12 (utility skills MUST NOT contain domain-specific constraints)
    rationale: |
      The "docs/stack/<lib>/<topic>.md" convention is maintainer-specific
      (it is how the maintainer organizes stack references in their
      projects). Other consumers of this skill via `npx skills add` will
      receive a utility that writes folders into their active project —
      they must either adopt the convention or override the target path
      (see SKILL.md "Deployability caveat").
    approved_by: maintainer
    date: 2026-07-22
---

# get-docs — ground the project's stack in live documentation

Parametric knowledge of large open-source repos goes stale fast. Context7
indexes them as snippets and serves them via a free REST API or the `ctx7`
CLI. This skill **fetches** the docs and then **persists them inside the
active project** so any LLM or harness that later operates on that project
finds the grounded docs locally instead of re-fetching from the internet.

The skill exists because the **stack is stable** for the duration of a
project (one chosen ORM, one chosen UI lib, one chosen auth provider) but
without grounding, each new agent session re-discovers the stack from
scratch. Once the stack has been picked — usually after the `design` or
`spec` loop — `get-docs` materializes the relevant Context7 snippets into
`docs/stack/<lib>/<topic>.md` and the cost is paid **once**.

## ⚠️ Deployability caveat (read first)

This skill writes markdown files into the **active project** under
`docs/stack/<lib>/<topic>.md`. It is the only utility in this repo with
this behavior; it is intentional (see `metadata.architecture_exception`
in the frontmatter) but it has consequences:

| If you... | Then... |
|---|---|
| Install this repo via `npx skills add` on **your own projects** | You'll get a `docs/stack/` folder created when the skill runs. Adopt the convention or override the target path (see "Override target" below). |
| Run this on **this repo** (agent-skills itself) | It will write into the local `docs/stack/`. Avoid running it on this repo — it is a meta-repo, not a project target. |
| Run this on **someone else's repo** | It will write files into their working tree without asking. Use with care. |

To opt out of the materialization and keep this skill as a pure fetcher,
set `GET_DOCS_MATERIALIZE=0` in the environment. The skill then returns
the snippets in the chat reply without writing any file.

## Wire your agent (one-time, manual)

Before the skill can do useful work, your agent needs to know about the
Context7 CLI. Run **once** per machine (or per project):

```bash
# Global, default mode (CLI + Skills, no MCP server, skip prompts)
npx -y ctx7 setup --cli -y

# OR: project-scoped (recommended — does not touch ~/.config globally)
npx -y ctx7 setup --cli -y -p

# OR: for a specific agent (Claude Code, Cursor, OpenCode, etc.)
npx -y ctx7 setup --claude -y -p     # or --cursor, --opencode, --antigravity, etc.
```

`setup` is **interactive by default** (`-y` makes it non-interactive).
The skill cannot run it for you — it modifies the user's agent config,
which is a human decision. The skill verifies in STEP 0 that the CLI
is reachable via `npx` and only fails loud if `npx` itself is missing.

If you do **not** wire your agent, the skill still works — it falls
back to the REST API. You just lose the CLI's nicer output formatting
(auth, pagination, consistent formatting across queries).

## When (self-trigger)

- The user says **"ground the stack"**, **"materialize docs for X"**,
  **"fetch docs for this project"**, or names a library in the context
  of a project with no `docs/stack/<lib>/` folder yet.
- A `design` or `spec` artifact just chose a new library and the user
  asks **"now get me the docs"** or **"ground me on this lib"**.
- The agent is about to use a library API it has not grounded yet
  (parametric knowledge older than training cutoff, fast-moving repo).
- The user names **"context7"**, **"ctx7"**, **"live docs"**, or
  **"fresh docs"** in a project context.

It does **NOT** fire on:

- General web search (use `web_search` / `web_extract`).
- Academic paper search (use `research-literature`).
- Library docs unrelated to an active project (use the bare Context7
  query — Context7 is the docs side, `api-credentials` is the keys side).

## STEP 0 — Ensure backend

On first invocation, the skill checks that the `ctx7` CLI is reachable
via `npx`. **No install.** `npx -y ctx7@latest` downloads to the npx
cache (~/.npm/_npx) on first use and reuses it on subsequent calls.

```bash
# (a) npx itself available?
if ! command -v npx >/dev/null 2>&1; then
  echo "WARN: npx missing (no Node.js). Using REST API fallback." >&2
  BACKEND="rest"
else
  # (b) npx can reach ctx7? Cold call ~0.7s, warm ~0.6s.
  if npx -y ctx7 --version >/dev/null 2>&1; then
    BACKEND="cli"
  else
    echo "WARN: npx ctx7 unreachable (network down or package issue). Using REST API fallback." >&2
    BACKEND="rest"
  fi
fi
```

Failure modes the skill handles without erroring out:

| Failure | Fallback |
|---|---|
| `npx` missing (no Node.js) | REST API only |
| `npx -y ctx7` fails (network down, npm registry unreachable) | REST API only |
| `ctx7 --version` exits non-zero | REST API only |
| User opted out with `GET_DOCS_BACKEND=rest` | REST API only (overrides detection) |

The skill logs which backend it is using in the first line of its
output so the user can see what ran.

## STEP 1 — Resolve library

```bash
npx -y ctx7 library <name>          # e.g. npx -y ctx7 library firecrawl
# -> /firecrawl/firecrawl-docs
```

Trust signals to inspect in the output (see "Trust signals" below):
`state`, `verified`, `trustScore`, `lastUpdateDate`. If any are weak,
flag them in the materialized doc's frontmatter.

## STEP 2 — Fetch snippets for a topic

```bash
npx -y ctx7 docs <id> <topic>       # e.g. npx -y ctx7 docs /firecrawl/firecrawl-docs "self-host OPENAI_BASE_URL"
# -> markdown snippets with source URLs and lastUpdateDate inline
```

The output is what gets materialized. Capture stdout verbatim.

## STEP 3 — Materialize (writes to the active project)

**Path contract**: `<project-root>/docs/stack/<lib>/<topic>.md`

Where:

- `<project-root>` is the directory the user is currently operating in
  (the agent's CWD, or the active plan's repo root if one is selected).
- `<lib>` is the library slug (lowercase, hyphenated, matches the
  Context7 ID's tail — `firecrawl-docs` → `firecrawl-docs`, `next.js`
  → `next.js`, etc.).
- `<topic>` is a slug of the user's topic query, kebab-cased.

**Frontmatter the skill writes** (every materialized file):

```yaml
---
library: firecrawl-docs          # Context7 ID (or shorthand slug)
topic: self-host OPENAI_BASE_URL
source_url: <first source URL from the snippet>
last_update: 2026-07-21          # from snippet's lastUpdateDate
trust_score: 9                   # from library output (1-10)
materialized_by: get-docs
materialized_at: 2026-07-22      # ISO date, today
---
```

**Dedupe rule** (run before writing):

1. If `docs/stack/<lib>/<topic>.md` **does not exist** → write it fresh.
2. If it **exists and is `< 30 days` old** (compare `materialized_at`)
   and the upstream `last_update` has not moved → **skip the write**,
   return a one-liner: `Already current (<lib>/<topic>, N days old)`.
3. If it **exists and is `>= 30 days` old** OR upstream `last_update`
   has moved → **prepend** a `_Refreshed: <date> — upstream moved from
   <old last_update> to <new last_update>_` line at the top of the body,
   then rewrite the snippet content below it.

**Override target**: set `GET_DOCS_STACK_DIR=/some/other/path` in the
environment to redirect the writes. Useful for monorepos with multiple
project roots, or for testing in a sandbox.

## STEP 4 — Triangulate (high-stakes builds only)

Context7 alone is **not enough** for a high-stakes build decision (a
config that will go into production, a docker-compose that takes 10 min
to build, etc.). Pair it with two cheap checks:

1. **GitHub raw** — `curl -sSL https://raw.githubusercontent.com/<owner>/<repo>/main/<path>`
   for the actual `docker-compose.yaml`, `Dockerfile`, `.env.example`.
   Use `main`, not tagged releases, unless you specifically need an old version.
2. **Pre-flight** — `docker compose --env-file .env config` (or equivalent)
   to confirm YAML parses, env vars expand, override files apply.
   Catches the entire class of "I built the wrong image because of an
   env typo" errors before they cost a rebuild.

The skill materializes the Context7 snippet first (cheap), then suggests
the triangulation steps to the agent. The agent decides whether to
execute them.

## Trust signals (Context7 output)

| Signal | Where to find it | Green flag |
|---|---|---|
| `state` | `ctx7 library` output | `"finalized"` |
| `verified` | `ctx7 library` output | `true` |
| `trustScore` | `ctx7 library` output | `>= 8` |
| `lastUpdateDate` | snippet header / library output | `< 12mo` |

**Never trust a `state != "finalized"` or `verified: false` snippet for
a high-stakes decision.** The skill surfaces these in the frontmatter
(`trust_score`) so future reads see the warning.

## When Context7 lies or is silent

Three known classes of silent failure (full list in
`references/context7-pitfalls.md` if present):

- **Embeddings on OpenRouter** — `/v1/models` does NOT list embedding
  models even though `google/gemini-embedding-2` exists. Confirm
  directly with `curl .../embeddings`; do not trust the models list.
- **Endpoint mismatches** — OpenAI-compatible providers expose either
  `/v1/chat/completions` (legacy) or `/v1/responses` (new). Most
  models on OpenRouter support both, but some only one. The fix is in
  the provider's model card, not in Context7.
- **Deprecated endpoints** — some services return
  `{"success":true,"id":"...","replacement":"/v2/scrape"}` and tell you
  to use a newer path. Always grep the source for `deprecat` if a
  "natural" endpoint misbehaves.

## REST API fallback (when `ctx7` is unavailable)

Base: `https://context7.com/api/v1`

```bash
# Search
curl -sSL "https://context7.com/api/v1/search?query=firecrawl+self-host" \
  | python3 -c "
import json, sys
for r in json.load(sys.stdin).get('results', [])[:5]:
    print(r['id'], '|', r.get('lastUpdateDate',''), '|', r.get('state',''))"

# Snippets by topic
curl -sSL "https://context7.com/api/v1/<owner>/<repo>?type=txt&topic=<urlencoded-topic>"
```

The skill wraps these calls when the CLI is missing. Output is
formatted to match `ctx7 docs` so STEP 3 (materialize) works the same
way regardless of backend.

## Pitfalls

- **Unverified repos can be AI summaries.** `verified: false` or
  `state != "finalized"` may have been generated, not scraped. The skill
  stamps `trust_score` in the frontmatter; readers should treat low
  scores as a warning, not a blocker.
- **Context7 doesn't replace the repo for code reading.** It indexes
  docs, not source. If you need to read implementation, you still need
  a clone — just a targeted one with `sparse-checkout` after Context7
  tells you which paths matter.
- **Topic parameter is fuzzy, not exact.** "self-host" may return docs
  that mention it in passing. Read the source URL at the top of each
  snippet to confirm it's the doc you actually wanted.
- **Rate limits.** Context7 free tier is generous for ad-hoc lookups;
  for batch research, dispatch subagents and have them each run their
  own queries to stay under any per-IP caps.
- **`ctx7` is a young CLI (0.5.x).** Pin a known-good version in
  `package.json` if your harness runs scripted upgrades.
- **Materialization is one-way.** The skill appends a `_Refreshed:` line
  on dedupe but does not edit the body of existing files. If you need
  to rewrite, delete the file and re-run.
- **When `npm i -g ctx7` actually makes sense.** `npx` adds ~0.6s per
  call (negligible for 1-5 calls per session). For agents that fire
  hundreds of doc queries per session (rare, but possible in batch
  research), or CI environments where npx cache can't be reused, a
  global install saves real time. Default: don't install; only switch
  if you measure the latency.

## Out of scope

- Full repo cloning (use `git clone` directly; `sparse-checkout` once
  Context7 tells you which paths matter).
- Web search across the open web (use `web_search` / `web_extract`).
- Academic paper search (use `research-literature`).
- Auto-detecting the project's stack from code (no AST analysis).
- Pre-fetching docs at session start (requires adapter changes, out of
  scope for this version).

## Related

- `research` — invokes this as a primary-source oracle when external
  facts are needed before build.
- `use-firecrawl` — concrete example of grounding a single library end
  to end (Firecrawl self-host). Owns the Firecrawl-specific knowledge;
  `get-docs` is the generic materializer.
- `api-credentials` — often used in conjunction; Context7 is the docs
  side, `api-credentials` is the keys side.
- `design` / `spec` — natural upstream triggers: when they pick a
  library, follow up with `get-docs` to ground it.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `GET_DOCS_MATERIALIZE` | `1` | Set `0` to disable FS writes (fetcher-only mode). |
| `GET_DOCS_STACK_DIR` | `<cwd>/docs/stack` | Override the target directory. |
| `GET_DOCS_FRESHNESS_DAYS` | `30` | Skip-write threshold. |
| `GET_DOCS_BACKEND` | auto-detect | Force `cli` or `rest`. Useful when npx is reachable but slow. |
