# LESSONS — use-herdr skill refinement (2026-07-31)

## L1. Verify subagent claims against the live binary, not just the repo

Subagent 2 reported the broken `--json` flag in the skill, citing
`herdr --json workspace create` → "unknown option: --json". I trusted-but-
verified by running the command myself before propagating the fix. This
turned out to be the most important single finding of the research party —
a critical correctness bug that had shipped in the skill 3 days earlier
and would have stayed silent until an agent actually tried the pattern
in production.

**Invariant:** when a subagent reports a fact about an executable CLI,
the parent SHOULD run at least one verification command before applying
the fix. Agents can be right about WHAT but wrong about WHY or wrong
about the exception cases (the binary rejects `--json` on creational
verbs but accepts it on a small set of others; subagent 2 captured the
fine-grained truth correctly only because I cross-checked it).

## L2. There are two copies of the skill and only one is the source of truth

The user has a personal agent-skills repo at
`~/Documents/Projects/agent-skills/` (the canonical source, where
`skill-forge audit` runs and where git history lives) and an installed
copy at `~/.agents/skills/use-herdr/` (loaded by pi via a symlink in
`~/.pi/agent/skills/use-herdr → ~/.agents/skills/use-herdr`). The two
were silently out of sync before this task: the installed copy was
newer (per `mtime`) and had subtle differences from the repo. I
initially edited only the installed copy; the audit kept passing
because it ran against the repo. Lesson: when editing a skill, edit
the repo copy and propagate, OR verify the audit path matches the edit
path.

**Invariant:** when applying skill edits, edit the repo copy first
(`~/Documents/Projects/agent-skills/<layer>/<name>/`) and `cp` the
changed files to `~/.agents/skills/<name>/` (the installed copy) so
both stay in lockstep. The audit runs against the repo; the runtime
loads from the installed copy.

## L3. "Recent release" can mean stable OR preview — check before documenting

The user said "recent release of herdr." I assumed v0.7.5 (latest
stable, 2026-07-21). But there were two PREVIEW builds newer than
0.7.5 (2026-07-29, 2026-07-21). Reading both surfaced several preview-
only changes (grok integration source-merged but not shipped, `pane
read` truncated-read reporting, `agent prompt` submission timing,
MIT→Apache-2.0 relicense) that would have been **wrong to document**
in a skill targeting the stable release. Discipline: when a skill
targets a stable tool, document stable; treat preview-only changes as
a "pending review" note in RESEARCH.md, not a SKILL.md edit.

**Invariant:** skill edits target the stable release the binary
actually exposes. Preview-only changes go in RESEARCH.md under a
"do-not-document-yet" section, not in the skill body. When the stable
release catches up, promote them.

## L4. `--json` is selectively supported across herdr CLI verbs — surprising default

Of ~25 verbs the skill uses, only 7 accept `--json` (status, session
list, server agent-manifests + update-agent-manifests, plugin list,
worktree list, agent explain). The rest output JSON to stdout by
default. The skill's claim "All commands accept `--json` for machine-
readable output" (in both `commands.md` line 20 and `topology.md` line
45) was false — and worse, the explicit `herdr --json <create-command>`
examples in the body actively error out. Future skills taught against
this binary MUST capture the actual contract:

| Verb family | Default output | `--json` flag |
|---|---|---|
| Creational (workspace create, pane split, tab create, etc.) | JSON | **rejected** |
| List/inspect (workspace list, pane list, agent list, worktree list) | JSON | **rejected** |
| Top-level status (`herdr status`) | YAML | required for JSON |
| `session list` | text table | required for JSON |
| `plugin list` | text | required for JSON |
| `server agent-manifests` | text | required for JSON |
| `agent explain` | text | `--format text\|json` |

**Invariant:** when documenting a CLI that mixes JSON-by-default and
text-by-default verbs, never generalize. Capture each verb family's
default explicitly. Pipe-without-`--json` first, fall back to
`--json` only if the response is not JSON.

## L5. Subagents can over-report — and the parent should grade

Subagent 3 reported spelling bugs `mastracade` → `mastracode` and
`qoder` → `qodercli` in the skill. I verified by grep: the skill
already had the correct spellings. The subagent either (a) read an
older snapshot of the skill files, or (b) inferred the bugs from the
binary source code without double-checking the docs. Either way, the
report was a false positive. I caught it because I always grep before
editing. Without the verify step, I would have applied 3 no-op
"fixes" to files that didn't need them.

**Invariant:** when a subagent reports a bug in a specific file, the
parent SHOULD `grep` for the claimed buggy string in the file before
applying the fix. Subagents reason well about external sources
(here, the herdr binary) but can mismatch against the docs that are
the actual edit target.

## L6. The community surfaces a different signal than the changelog

Subagent 4 (docs + community) found three issues that the GitHub
release notes summarized as one-liners and that I would have missed
without a community scan: headless-restart + `agent prompt` returns
`agent_not_found` (#2065), herdr-inside-tmux failures (#2054, #2057),
non-US keyboard `send-keys` regression (#1992). None of these appear
in the v0.7.5 release notes. They appear only in issues and HN
threads. For a skill that drives the tool from another agent,
catching these is the difference between a skill that works in
Andrés's normal setup and a skill that breaks on first run.

**Invariant:** when refining a domain skill, dispatch one subagent
specifically to GitHub issues (last 30d) + HN/Reddit. The release
changelog undercounts the gotchas that matter for production use.
