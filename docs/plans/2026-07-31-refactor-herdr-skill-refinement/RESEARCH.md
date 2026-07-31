# RESEARCH — herdr changes since 0.7.5

> Synthesized from 4 parallel research subagents (releases, CLI diff, integrations,
> docs+community). Each finding cites the source. Installed binary: herdr 0.7.5
> (verified `herdr --version` → `herdr 0.7.5`).

## TL;DR

The skill is **structurally aligned** with v0.7.5 stable, but contains:
- **1 critical correctness bug**: every `herdr --json <create-command>` example errors
  out. The `--json` flag is selectively supported; on creational commands the binary
  outputs JSON by default. Remove `--json` from the creational commands in the skill.
- **1 spelling bug**: skill says `mastracade`, binary + repo use `mastracode`.
- **1 short alias bug**: skill says `qoder`, binary uses `qodercli`.
- **1 false claim**: "All commands accept `--json`" — only 7 commands do.
- **6 minor additions** for things that landed in v0.7.5 but the skill missed.
- **2 community-reported gotchas** worth adding to boundaries.
- **Several preview-only changes** (2026-07-29 build) — DO NOT document yet,
  preview is not stable.

## A. Releases & changelog (subagent 1)

### Timeline
- v0.7.3 (2026-07-07): bugfix only.
- v0.7.4 (2026-07-15): popup floating panes, `ui.copy_on_select`, Maki kind.
- v0.7.5 (2026-07-21): **breaking** (plugin state global). New live-agent CLI
  facade (`agent start/prompt/send-keys/wait`), `agent.view.set/clear` (socket
  API only — NOT a CLI subcommand), `[[startup]]` plugin hooks,
  `ui.sidebar_start_collapsed`, `ui.prompt_new_workspace_name`, `HERDR_AGENT`
  env var (macOS). Old `wait` removed; `agent send` → `agent send-keys`.
- preview-2026-07-29-44b3adb12552: major preview. grok native session restore,
  filterable keybind help, bundled agent SKILL.md. Fixes: system notifications
  on Windows, worktree label preservation, agent prompt submission timing,
  truncated pane reads reported, nested codex session reports ignored, hermes
  lifecycle hardening, ConPTY bundling. Perf: spinner removal, hidden PTY
  render skip, workspace git-discovery cache. **CHORE: relicense to Apache-2.0.**

### Skill-impacting (in v0.7.5 stable — must reflect)
| Change | Source | What to fix |
|--------|--------|-------------|
| `HERDR_AGENT=<agent>` env var (macOS) | v0.7.5, commit 947328f | Add to SKILL.md §"Caller context" and topology.md env-var table |
| `herdr config check` subcommand | v0.7.5, commit f11be93 | Add to commands.md Config section |
| `herdr api snapshot` subcommand | v0.7.5 (implied) | Add to commands.md Socket API section |
| `ui.sidebar_start_collapsed` | v0.7.5, commit 9c9490d | Mention in commands.md Config section |
| `ui.prompt_new_workspace_name` | v0.7.5, commit e298e45 | Mention in commands.md Config section |
| `agent.view.set/clear` (socket API) | v0.7.5, commit d30ab1b | Already in agent-integrations.md (socket API only — NOT a CLI verb) |

### Preview-only — DO NOT document
- `pane read` truncated-read reporting (preview, commit c0fb777)
- `agent prompt` submission timing change (preview, commit bb29eed)
- Relicense MIT → Apache-2.0 (preview, commit cd5ea1b)

## B. CLI surface vs installed binary (subagent 2)

### Verified v0.7.5 binary surface
- 17 top-level subcommands: server, api, completion, config, channel, workspace,
  worktree, tab, notification, agent, pane, session, integration, plugin,
  terminal, status, update.
- 21 `--kind` values for `agent start` — exact match with skill.
- Env vars documented in `--help`: only `HERDR_CONFIG_PATH`. Skill's 10 env vars
  are runtime-injected (HERDR_ENV, HERDR_PANE_ID, etc.) — the binary sets them
  in pane processes; `--help` just doesn't enumerate them. Skill is correct.

### CRITICAL: `--json` flag bug

| Command | `--json` accepted? | Behavior without `--json` |
|---------|--------------------|--------------------------|
| `status` | yes | JSON to stdout |
| `session list` | yes | JSON to stdout |
| `server agent-manifests` | yes | JSON to stdout |
| `server update-agent-manifests` | yes | JSON to stdout |
| `plugin list` | yes | JSON to stdout |
| `worktree list` | yes | JSON to stdout |
| `agent explain` | yes (`--format text\|json` also available) | text by default |
| `workspace create` | **NO — rejects with "unknown option: --json"** | JSON to stdout |
| `pane split` | **NO** | JSON to stdout |
| `tab create` | **NO** | JSON to stdout |
| `workspace get` | **NO** | JSON to stdout |
| `pane get` | **NO** | JSON to stdout |
| `tab get` | **NO** | JSON to stdout |
| `workspace close` | **NO** | JSON to stdout |
| `pane list` | **NO** | JSON to stdout |
| `agent list` | **NO** | JSON to stdout |
| `workspace list` | **NO** | JSON to stdout |
| `tab list` | **NO** | JSON to stdout |

**Implication:** every `herdr --json <create-command> | python3 -c 'import json...'`
example in SKILL.md and references/workflows.md is broken. The pipe-parser
pattern still works IF the `--json` flag is removed (the binary outputs JSON
to stdout by default for creational commands).

**Fix:** strip `--json` from creational-command examples. The
`herdr --json <create-command>` form has to become `herdr <create-command>`.

### JSON response shape
- Socket API and CLI both return `{ "id": "...", "result": { ... } }` envelope.
- Skill's `.result.workspace.workspace_id` paths are **correct** for both.
- `workspace.create` returns `.result.workspace.workspace_id`,
  `.result.tab.tab_id`, `.result.root_pane.pane_id` (matches skill).
- `pane.split` returns `.result.pane.pane_id` (matches skill).
- `tab.create` returns `.result.tab.tab_id` (matches skill).

### Defaults
- `[experimental].pane_history = false` is **uncommented** in default config
  (active default). Skill implies both `pane_history` and `kitty_graphics`
  are commented experimental opt-ins — partially wrong.
- `cjk_ime_agents` comment lists `qoder` and `qodercli` as separate — but
  the CLI only accepts `qodercli`. This is just a config comment, not a CLI
  surface issue.

## C. Agent integrations (subagent 3)

### `--kind` list — verified exact match
`pi, claude, codex, gemini, cursor, devin, agy, cline, omp, mastracode, opencode,
copilot, kimi, kiro, droid, amp, grok, hermes, kilo, qodercli, maki` (21 total).

### `herdr integration install` — 14 supported
`pi, omp, claude, codex, copilot, devin, droid, kimi, opencode, kilo, hermes,
qodercli, cursor, mastracode` (verified via
`herdr integration install grok` → "unknown integration target" error message).

### Spelling bugs (in the skill)
| Wrong (in skill) | Right (binary + repo) | Files |
|------------------|------------------------|-------|
| `mastracade` | `mastracode` | SKILL.md body, references/agent-integrations.md, references/commands.md |
| `qoder` (in session-identity list) | `qodercli` | references/agent-integrations.md |

### Grok integration: source-merged, NOT in 0.7.5 binary
- `IntegrationTarget::Grok` merged in commit `e9b22084` (2026-07-24).
- 0.7.5 has `grok` as detectable `--kind` (screen manifest) but
  `herdr integration install grok` errors "unknown integration target."
- Will ship in next release. **Do not document yet** — preview-only.

### Agent authority model (verified)
- **Lifecycle authority** (7): pi, omp, kimi, opencode, kilo, hermes, mastracode
- **Session identity only** (8): claude, codex, copilot, devin, droid,
  qodercli, cursor, grok
- **No integration (screen manifest only)** (6): gemini, agy, cline, kiro,
  amp, maki

Note: previous skill memory said "lifecycle authority = pi/omp/kimi/opencode/
kilo/hermes/mastracode" (6 agents) — that's correct on 0.7.5 since grok
integration is not yet shipped. Once 0.7.6 ships, grok moves from "screen
manifest only" to "session identity only" (it's screen-manifest for state,
not lifecycle authority).

## D. Docs & community (subagent 4)

### Docs site (https://herdr.dev/docs/)
- 15 pages, last build Jul 30, 2026. Dropdown shows 0.7.5 stable + Unreleased
  preview channel.
- Config sections on the site: 20+ sub-pages (keybindings, theme, ui-and-sidebar,
  terminal-defaults, notifications, logs, agent-session-restore, remote-attach,
  worktrees, advanced-configuration, custom-command-keybindings,
  environment-variables, ime-cursor-tracking, indexed-jumps, kitty-graphics,
  prefix-input-source-switching, reload-config, sidebar-row-layouts, sound).
- The skill's `Config` section in SKILL.md only mentions `[terminal]`,
  `[worktrees]`, `[keys]`, `[theme]`, `[ui]`, `[session]`, `[experimental]`
  — this is a summary, not a full table. The reference should be the
  authoritative list.

### GitHub issues that affect skill accuracy
- **#2065** [open]: After headless restart, `agent list` reports agents idle
  but `agent prompt` returns `agent_not_found`. Workaround: attach a client
  first. **Add a MUST to the skill's boundaries.**
- **#2012** [needs-decision]: `pane current` trusts inherited `$HERDR_PANE_ID`,
  reports wrong workspace's pane. Skill uses `--current` heavily; document a
  caveat.
- **#1992** [pending-release, fixed on master]: Shifted punctuation on
  non-US keyboards (e.g. Spanish `/` = Shift+7) not handled. Fix is on master
  but not yet in 0.7.5. **Add a warning to boundaries** for non-US keyboards
  using `send-keys`.
- **#2008** [pending-release, windows]: Windows/OpenSSH logout kills
  detached herdr server.
- **#2020** [pending-release]: Vibe CLI text input broken (kitty protocol
  regression) post-0.7.5.

### Community sentiment
- HN: 9 results, 60 days. Show HN Jul 2 had 404pts / 178 comments. Sentiment
  mostly positive — "completely replaced tmux" is a recurring comment.
  - Top complaints: copy mode "very basic" vs tmux, herdr-inside-tmux
    problems (mouse/keybinds fail), non-US keyboard issues, context
    switching between agents.
- Reddit: no results.

### Workflows the site documents that the skill mentions (already)
- `agent start` with `--kind` and `--` forwarding — covered.
- `herdr integration install/uninstall` — covered in agent-integrations.md.
- `agent explain --json` — covered in commands.md.
- `agent-session-restore` config — covered in agent-integrations.md.
- `herdr --remote` and remote access — covered in topology.md.

### Workflows the site documents that the skill does NOT mention
- `agent.view.set/clear` (socket API) — already in agent-integrations.md
  (low impact for CLI users).

## Concrete refinement plan

### SKILL.md edits
1. Strip `--json` from Workflow A and C creational-command examples.
2. Fix `mastracade` → `mastracode` in Workflow D `--kind` list.
3. Add `HERDR_AGENT=<agent>` to the "Caller context" env var section.
4. Add a "Known issues" subsection under Boundaries (or extend Boundaries)
   with the herdr-inside-tmux gotcha, headless-restart gotcha, and
   non-US-keyboard send-keys gotcha.

### references/commands.md edits
1. Fix `mastracade` → `mastracode` (in any `agent start` notes or kind
   references).
2. Add `herdr config check` to the Config section.
3. Add `herdr api snapshot` to the Socket API section.
4. Rewrite the "All commands accept `--json`" claim to be accurate (it
   only applies to a small subset).
5. Add `ui.sidebar_start_collapsed` and `ui.prompt_new_workspace_name`
   to the Config section.
6. Note that `[experimental].pane_history` is uncommented (active default).

### references/agent-integrations.md edits
1. Fix `mastracade` → `mastracode` everywhere.
2. Fix `qoder` → `qodercli` in the "Session identity only" row.

### references/topology.md edits
1. Add `HERDR_AGENT` to the env-vars table.

### references/workflows.md edits
1. Strip `--json` from Workflow A and C creational-command examples.
