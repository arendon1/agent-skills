# PRD — get-docs (utility skill, ex-`ctx7`)

> Plan: `2026-07-22-refactor-get-docs` · Layer: utility · Author: Hermes + maintainer

## Mission

Ground any agent (LLM/harness) operating on the active project in the project's
tech stack by fetching live documentation via the **Context7 CLI** (`ctx7`,
fallback: REST API) and materializing the relevant snippets as markdown
references under **`docs/stack/<lib>/<topic>.md`** in the project root.

The skill exists so the agent does not re-fetch the same docs from the internet
on every session, once the stack has stabilized after the refinement pipeline
(`grill` → `design` → `spec`).

## Why this exists (the problem)

Today the `ctx7` (ex `context7-live-docs`) skill is **reactive**: every time the
agent hits a docs question it re-hits Context7. Cost & latency aside, the real
issue is that the **stack is stable** for the duration of a project (one
chosen ORM, one chosen UI lib, one chosen auth provider) but the agent treats
each query as if it were discovering the stack from scratch. The maintainer's
explicit goal: stop re-paying the cost once the stack has been picked.

## Scope

### In scope

1. **Backend ensure**: on first invocation, install `ctx7` CLI globally via
   `npm install -g ctx7`. Verify with `ctx7 --version` (expect 0.5.5+).
   Degrade to the REST API fallback (`https://context7.com/api/v1`) if
   install fails (no Node.js, no write access, no network).
2. **Resolve** library name → Context7 ID via `ctx7 library <name>`.
3. **Fetch** snippets for a topic via `ctx7 docs <id> <topic>`.
4. **Materialize** the most relevant snippets as
   `<project-root>/docs/stack/<lib>/<topic>.md`, frontmatter-rich
   (source URL, `lastUpdateDate`, trustScore, snippet body).
5. **Dedupe**: if `<lib>/<topic>.md` already exists and is `< 30 days` old
   AND `lastUpdateDate` in the doc hasn't moved, skip the write. Else
   append a `_Refreshed: <date>` line at the top.
6. **Triangulate** (high-stakes builds only): Context7 + raw GitHub
   `main` + `docker compose --env-file .env config` (or equivalent).

### Out of scope

- Auto-detecting the stack from a project (no code analysis).
- Pre-fetching docs at session start (would require adapter changes — out).
- Editing/mutating existing `docs/stack/<lib>/<topic>.md` beyond the
  refresh-line + snippet body. The skill does **not** rewrite project
  prose or code.
- Reading or merging into `CONTEXT.md` of the consuming project.

## Architecture exception (declared, not silent)

AGENTS.md §12 says utility skills MUST NOT contain domain-specific
constraints. This skill knowingly violates that rule because the
"docs/stack/..." convention is **maintainer-specific** (it is how the
maintainer organizes stack references in their projects). Other consumers
of `npx skills add <this-repo>` will receive a utility that writes
folders into their active project — they must either adopt the
convention or override the target path. Documented in the skill's
SKILL.md under "Deployability caveat".

The exception is **declared in the frontmatter** under
`metadata.architecture_exception` so future audits / readers can see
the rationale without re-deriving it from §12.

## Triggers (when this fires)

`invocation: auto`. Self-triggers when:

- User says "ground the stack", "materialize docs for X", "fetch docs for
  this project", or names a library in the context of a project with no
  `docs/stack/<lib>/` folder.
- A `design` or `spec` artifact just chose a new library and the user
  asks "now get me the docs".
- The agent is about to use a library API it has not grounded yet
  (parametric knowledge older than training cutoff).

It does NOT fire on:

- General web search (use `web_search` / `web_extract`).
- Academic paper search (use `research-literature`).
- Library docs unrelated to an active project (use the bare `ctx7` query).

## Success criteria

- After running, `<project-root>/docs/stack/<lib>/<topic>.md` exists
  with a valid frontmatter (source URL, lastUpdateDate, trustScore).
- A second run for the same `<lib>/<topic>` does not duplicate or
  clobber; it refreshes the date line.
- If `ctx7` is missing and install fails, the REST API fallback is used
  with no user-visible error.
- `skill-forge audit.py get-docs` → exit 0.
- `manifest.py --check` → exit 0.

## Non-goals (explicit)

- **No adapter changes.** The self-trigger is via the `Use when` line in
  frontmatter; the adapter (`adapters/hermes/`) is not touched.
- **No AGENTS.md changes.** The §12 rule stays as is; this skill
  declares its own exception locally.
- **No CLI shim** beyond `ctx7` + REST fallback. No custom wrapper.
