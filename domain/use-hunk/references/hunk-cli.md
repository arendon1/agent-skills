# hunk CLI — minimal reference for the orchestration layer

This is a SUBSET of the hunk session API. The full, authoritative
surface is the skill file hunk itself ships — print its path with
`hunk skill path` and load it as a transient resource when the agent
needs to do anything beyond what is listed here.

**Do not vendor the full hunk-review skill into use-hunk.** hunk ships
its own; the agent loads it on demand. This file exists so the
orchestration layer (use-hunk) can describe the API without
duplicating it.

## Two distinct hunk surfaces

The hunk CLI has two halves. The agent uses ONLY the second.

| Half | Commands | Audience |
|---|---|---|
| User-facing TUI | `hunk diff`, `hunk show`, `hunk patch`, `hunk pager`, `hunk difftool`, `hunk stash show` | operator opens these in a terminal |
| Agent-facing session API | `hunk session *`, `hunk skill path`, `hunk daemon serve` | the agent drives an already-open hunk TUI via the local session broker |

The agent MUST NOT call the user-facing TUI commands. Those are
interactive and will hang the agent's bash call. Only `hunk session *`
and `hunk skill path` are the agent's API.

## The session broker

When hunk starts, it registers with a loopback HTTP daemon
(`127.0.0.1:47657` by default; override with `HUNK_MCP_PORT`). The
agent's `hunk session *` commands talk to that daemon. If the agent
is in a sandbox that blocks loopback, fall back to printing the raw
patch in chat.

## Commands the orchestration layer actually calls

| Command | Purpose | When |
|---|---|---|
| `hunk --version` | confirm install | prerequisite check |
| `hunk skill path` | print the path to the bundled hunk-review skill | first pause in a session, to load the transient skill |
| `hunk session list [--json]` | list live sessions | verify session is alive before claiming "ready for review"; re-verify after long gaps |
| `hunk session get --repo .` | inspect a session's repo / path / source | when more than one session exists, to disambiguate |
| `hunk session review --repo . --json` | get file/hunk structure (NO raw patch) | after the operator's first message on a paused review, to confirm what's loaded |
| `hunk session review --repo . --include-patch --json` | same + raw unified diff text | only when the agent needs the raw patch for an inline note or to answer a question |
| `hunk session navigate --repo . --file X --hunk N` | move the live TUI to a specific hunk | before leaving an inline note, so the operator sees the code being discussed |
| `hunk session comment add --repo . --file X --new-line N --summary "..." [--focus]` | add one inline note | selective annotations on non-obvious decisions |
| `hunk session comment apply --repo . --stdin [--focus]` | add a JSON batch of notes | preferred when the agent has several notes ready; one batch beats many shell calls |
| `hunk session comment list --repo . --type user` | list operator-authored notes | if the operator left notes, the agent can iterate on them |

`hunk session reload --repo . -- diff <new-target>` is also useful when
the operator asks to see a different range (e.g. "show me the diff vs
main" or "show me the last commit"). The agent uses it via the
transient hunk-review skill, not directly in the orchestration code.

## Comment payload shape (for `comment apply`)

```json
{
  "comments": [
    {
      "filePath": "src/auth.ts",
      "newLine": 78,
      "summary": "Token rotation extracted to helper — verify TTL semantics",
      "rationale": "Old code rotated inline; new helper centralizes TTL. Same behavior expected; double-check the 'never refresh within last 5s of expiry' rule.",
      "author": "use-hunk"
    }
  ]
}
```

Required: `filePath`, `summary`, exactly one of `hunk`, `hunkNumber`,
`oldLine`, or `newLine`. Optional: `rationale` (extended context),
`markup` (STML, requires `--experimental` opt-in on the review).

## The `hunk skill path` integration

The hunk-review skill file is bundled with the brew install at
`<prefix>/libexec/skills/hunk-review/SKILL.md` (run `hunk skill path`
to get the exact path). The orchestration layer's first action on a
new pause is to load that skill transiently so the agent can use the
`hunk session *` commands with the right flags.

The orchestration layer does NOT vendor or duplicate that skill. The
agent loads it at runtime via whatever skill-loading mechanism the
host harness provides (e.g. `Skill` tool in some harnesses, or
manually reading the file at the printed path).

## What the agent does NOT need from hunk

- The user-facing TUI commands — operator runs those.
- The extension API — that's for power users adding custom themes /
  language backends; not relevant to orchestration.
- The OpenTUI component (`hunkdiff/opentui`) — that's for embedding
  the renderer in another TUI app; not relevant to orchestration.
- Direct broker HTTP calls — the CLI wraps them; the agent never
  curls `127.0.0.1:47657` directly unless the CLI is broken AND the
  agent sandbox permits it (rare escape hatch).

## Versioning

hunk releases roughly weekly (8 releases in 30 days as of v0.17.7).
The session CLI is stable across recent versions; new subcommands
land as opt-in flags (`--include-patch`, `--include-notes`,
`--experimental`). The orchestration layer SHOULD NOT pin to a
specific hunk version — gate on `command -v hunk` and let the
transient hunk-review skill handle version-specific surface.

If a new hunk release ships a breaking change to the session API, the
bundled hunk-review skill will be updated upstream; loading the
transient skill picks up the new behavior automatically.
