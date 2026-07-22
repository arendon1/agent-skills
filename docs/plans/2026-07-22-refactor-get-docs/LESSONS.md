# LESSONS — get-docs

> Plan: `2026-07-22-refactor-get-docs`. Bugs / learned invariants surfaced during build + verification.

## L1 — `ctx7 library <name>` returns N>1 candidates; first is not always right

**Date:** 2026-07-22
**Severity:** 🟡 WARN (correctness footgun)

### Symptom

`ctx7 library firecrawl` returns 5 candidates:

1. `/firecrawl/firecrawl-docs` — the *docs* repo (4302 snippets, score 83.6)
2. `/firecrawl/firecrawl` — the *SDK* repo (729 snippets, score 77.95)
3. `/websites/firecrawl_dev` — scraped website (3020 snippets, score 80.08)
4. `/llmstxt/firecrawl_dev_llms_txt` — `llms.txt` dump (8925 snippets, score 54.29)
5. `/firecrawl/firecrawl-mcp-server` — the MCP server repo (553 snippets, score 91.51)

The skill's STEP 1 (in v2.0.0) currently takes the top hit by score, which is
the MCP server here (score 91.51), NOT the docs (score 83.6). For the
"self-host OPENAI_BASE_URL" query the top hit happens to be the docs repo
because `ctx7 docs` ranking reorders, but for arbitrary queries the SDK or
MCP repo can win and the materialized `docs/stack/<lib>/<topic>.md` will
be mis-categorized.

### Root cause

`ctx7 library` returns a ranked list, not a single canonical ID. There is
no signal in the output that says "this is THE docs repo, the others are
related but distinct". The skill has to disambiguate by query intent
(`docs` vs `sdk` vs `mcp`) — that disambiguation is not implemented.

### Fix (proposed, not yet shipped)

In STEP 1, after getting N candidates:

1. If the query mentions "docs", "API reference", "self-host", or similar
   docs-y intent, prefer candidates with `/docs` or `/llmstxt/` in the ID.
2. If the query mentions "install", "import", "require", prefer the SDK.
3. If ambiguous, show the user the top-3 with one-line summaries and let
   them pick (or default to the top hit and surface the choice in the
   materialized frontmatter as `library: <chosen-id>` so it's traceable).

The materialized file should record which candidate was chosen so a
human reader can spot a mis-resolution. Current frontmatter uses
`library: <slug>` — expand to include the full Context7 ID:

```yaml
library:
  id: /firecrawl/firecrawl-docs   # full ID chosen
  slug: firecrawl-docs            # path slug derived
```

### Status

⚠️ **Documented, not fixed.** The E2E verification happened to pick the
right repo (because the query was docs-flavored). A general fix requires
the intent-classification step above. Filing here so the next iteration
of `get-docs` (or a future `grill` on this skill) picks it up.
