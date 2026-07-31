# ARD — use-hunk skill

## System context

```
operator (pi session)           ←→    agent (pi core)
  ↓ types "go" / "sigue" / "abort"        ↓
  ↓                                       ↓ pauses when triggered
  ↓ watches hunk TUI  ←→  hunk session  ←→ hunk session broker (loopback HTTP, 127.0.0.1:47657)
                                          ↑
                                       agent drives via `hunk session *` CLI
```

- hunk TUI = surface where the operator reads the diff. Lives in cmux pane, herdr pane, or operator's manual terminal.
- hunk session broker = loopback HTTP daemon started by hunk TUI. Agent drives via `hunk session list|get|context|review|navigate|reload|comment *`.
- agent = pi core, augmented by use-hunk skill (orchestration) + hunk-review skill (transient, loaded via `hunk skill path` for the CLI surface).

## Layers

| Layer | Skill | Role |
|---|---|---|
| 1 process | `build` (existing) | when about to commit, query use-hunk for pause decision |
| 2 domain | `use-hunk` (new) | decision: trigger, surface, preamble, inline notes, wait |
| 2 domain | `hunk-review` (transient, from `hunk skill path`) | CLI mechanics: inspect/navigate/comment |
| 2 domain | `use-cmux`, `use-herdr` (existing) | surface management: open/control pane |

use-hunk calls into use-cmux/use-herdr for surface; loads hunk-review transiently for CLI mechanics. use-hunk never speaks cmux/herdr/hunk CLI directly — it delegates.

## Decision points

### 1. Trigger — when to pause

```
operator said "revisar|review|pausa|para|hold|wait"?
  → yes: pause
  → no: continue
change crossed risk threshold?
  → yes: pause with reason
  → no: continue autonomously
```

Risk threshold (defaults; configurable in `~/.config/agent-skills/use-hunk.toml`):
- changed lines >= 80 OR
- files changed >= 4 OR
- touches: auth, security, schema, migration, secret, ci, lockfile OR
- introduces new dependency OR
- reverts prior change OR
- agent self-reports low confidence

### 2. Surface — where hunk runs

```
inside cmux?  → spawn cmux pane, run `hunk diff` there
else inside herdr? → spawn herdr pane, run `hunk diff` there
else → print: "run `hunk diff` in another terminal, then say go"
```

Detection: cmux = `command -v cmux` + cmux session env; herdr = `${HERDR_ENV:-} = 1`. Both may be true; prefer cmux (it's newer in this operator's stack). Manual = fallback.

### 3. Resume — what counts as "go"

Three buckets. Skill keeps the lexicon; ambiguity → flag and ask.

| Bucket | Patterns (es/en) | Action |
|---|---|---|
| approve | go, ok, dale, sigue, procede, ship, lgtm, ✓, +1, continue | next step |
| feedback | any other instruction-shaped message | iterate on the change |
| stop | cancel, abort, rollback, para, deten, stop, halt | revert (git restore) + ack |

Self-check: if message doesn't match any bucket AND isn't feedback-shaped, agent MUST flag ambiguity: "interpreté X como Y, ¿procedo? si no, ¿qué querías decir?".

### 4. Annotations

- Chat preamble (always, 2–3 lines): what changed, why, what to verify.
- Inline hunk notes (selective): only for non-obvious decisions, race conditions, migrations, breaking changes, follow-ups. Skip for trivial diffs.

## Data flow (per pause)

```
agent finishes unit of work
  ↓
use-hunk: trigger? (keyword OR risk)
  ↓ no
  continue
  ↓ yes
use-hunk: surface? (cmux → herdr → manual)
  ↓
agent writes preamble in chat
  ↓
agent opens hunk in chosen surface (or instructs operator)
  ↓
agent loads hunk-review transiently (`hunk skill path`)
  ↓
agent: `hunk session review --repo . --json` to verify session alive
  ↓
agent: `hunk session comment apply --stdin` for inline notes (if any)
  ↓
agent waits for operator message
  ↓
agent classifies message (approve | feedback | stop | ambiguous)
  ↓
  approve → next step
  feedback → iterate, re-pause at end
  stop → revert + ack
  ambiguous → flag, ask
```

## Interfaces

use-hunk's only public contract is: "given a unit of work, decide whether to pause and how." Process skills (e.g. build) call use-hunk at checkpoint boundaries; use-hunk does not call process skills.

```
use-hunk.request_pause(reason: str, diff_context: dict) -> PauseDirective
  PauseDirective = {
    should_pause: bool,
    surface: "cmux" | "herdr" | "manual",
    preamble: str,
    inline_notes: list[InlineNote] | None,
    reason: "keyword" | "risk" | "explicit"
  }
```

## Failure modes

| Failure | Behavior |
|---|---|
| hunk binary missing | fall back to manual `git diff` in chat; print install hint once |
| hunk session broker not running | print: "is hunk open in another terminal?"; wait |
| hunk session broker port blocked by agent sandbox | print raw patch in chat; ask "go?" |
| operator message in non-bucket lexicon | flag ambiguity, ask |
| risk threshold trigger on trivial diff | operator can override with "auto" keyword per request |
| mid-pause operator switches terminal | session broker re-resolves by `--repo .`; agent re-checks on each input |

## Boundaries (skill level)

**MUST**
- gate on `command -v hunk` before any hunk call
- prefer cmux over herdr when both available
- print preamble BEFORE pausing
- classify operator input into approve/feedback/stop/ambiguous on every message
- flag ambiguity explicitly — never assume
- load hunk-review skill transiently via `hunk skill path` rather than duplicating its CLI surface
- write annotations only for non-obvious decisions; never annotate trivial diffs

**MUST NOT**
- never run `hunk diff`/`hunk show`/`hunk patch` directly from the agent (those are user-facing TUI commands; only `hunk session *` is the agent API)
- never auto-resume without an explicit operator signal
- never silently skip the preamble
- never write inline notes that rephrase what the code already says
- never name a specific harness/model/tool in the body of the skill (per agent-skills §9)
- never modify hunk itself or ship patches upstream

## References

- `~/.config/hunk/config.toml` — hunk's own config (theme, mode, watch, etc.)
- `~/.config/agent-skills/use-hunk.toml` — use-hunk config (risk thresholds, surface preference, lexicon)
- `hunk skill path` — transient skill file for CLI mechanics (do not vendor)
- `use-cmux` skill — for surface when cmux is the multiplexer
- `use-herdr` skill — for surface when herdr is the multiplexer
