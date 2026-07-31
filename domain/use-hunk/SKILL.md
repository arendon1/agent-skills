---
name: use-hunk
description: |
  Orchestrate a pause-for-review workflow around the hunk terminal diff viewer.
  Decides when to pause (keyword + risk-aware), opens hunk in the active
  terminal multiplexer (cmux, herdr, or instructs the operator to launch it
  manually), prints a chat preamble, leaves selective inline notes on
  non-obvious decisions, waits for the operator's next message, and
  classifies it as approve / feedback / stop / ambiguous before proceeding.
  Use when the agent has just written or modified code and the operator may
  want to review it, when a change crosses the risk threshold (>= 80 lines,
  >= 4 files, auth/schema/migration/secret/lockfile/ci paths, new dependency,
  revert), when the operator says "revisar|review|pausa|para|hold|wait",
  when the agent is about to commit or push, when the operator asks to walk
  them through a changeset, or when the agent is not sure whether the
  operator wanted a review or autonomy and should flag the ambiguity.
invocation: auto
layer: domain
provides: [code-review-pause]
language: en-US
metadata:
  version: "1.0.0"
---

# use-hunk

Domain capability for orchestrating a code-review pause around the `hunk`
CLI (modem-dev, MIT, brew formula). hunk is a review-first terminal diff
viewer: the operator opens a TUI in one terminal, and the agent controls
that TUI from another via a local session broker. use-hunk sits above the
broker and answers four questions for every unit of work the agent
finishes: should we pause, where does hunk live, what do we annotate,
and what counts as "go".

This skill does NOT duplicate hunk's CLI surface. For the actual session
calls (`hunk session list|get|context|review|navigate|reload|comment *`),
load the skill file that hunk itself ships — print its path with
`hunk skill path` and load it as a transient resource. use-hunk is the
orchestration layer; the bundled hunk-review skill is the mechanics
layer.

## The model

Four decision points, evaluated in order, every time the agent is about
to commit, push, declare a task done, or hand back to the operator:

```
1. TRIGGER   should we pause?
2. SURFACE   where does hunk run?
3. ANNOTATE  what do we write before pausing?
4. RESUME    what does the operator's next message mean?
```

### 1. Trigger

Pause when ANY of the following is true. Otherwise proceed autonomously.

- **Operator keyword.** The operator's last message contains any of:
  `revisar`, `review`, `pausa`, `para`, `hold`, `wait`, `ver`, `mira`,
  `revisa`, `échale un ojo`, `check this`, `look at this`, `pause`.
- **Risk threshold.** The change crosses the configured safety net.
  Defaults (overridable in `~/.config/agent-skills/use-hunk.toml`):
  - changed lines >= 80, OR
  - files changed >= 4, OR
  - touched path matches auth / security / schema / migration / secret /
    lockfile / ci / .github / deploy, OR
  - new dependency added to a manifest (package.json, requirements.txt,
    pyproject.toml, go.mod, Cargo.toml), OR
  - reverts or undoes a prior change, OR
  - the agent self-reports low confidence on the change.
- **Explicit checkpoint.** The agent is about to commit, push, open a PR,
  merge, deploy, or hand back a long task. Pause by default at these
  boundaries unless the operator said `auto` for this request.

The agent's right-sizing heuristic: a one-line fix never pauses; a
non-trivial change never proceeds without the preamble.

### 2. Surface

Pick the surface in this order. The first match wins.

1. **cmux.** Detect with `command -v cmux` plus the cmux session marker
   (cmux sets its own env when inside one of its surfaces). If detected,
   load the `use-cmux` skill transiently and open `hunk diff` in a new
   cmux pane. Preferred when available — it is the operator's primary
   surface in this stack.
2. **herdr.** Detect with `test "${HERDR_ENV:-}" = 1`. If inside a herdr
   pane, load the `use-herdr` skill transiently and open `hunk diff` in a
   new herdr pane.
3. **Manual fallback.** Print the exact command and wait:
   `Run \`hunk diff\` (or \`hunk show HEAD\`) in another terminal, then
   say \`go\` or leave feedback.`

The agent MUST verify the hunk session is alive before declaring "ready
for review": `hunk session list --json`. If empty, the chosen surface did
not actually start hunk — print the manual command as fallback and wait.

### 3. Annotate

Two surfaces, two rules.

**Chat preamble (always, 2–3 lines).** Print BEFORE pausing. Format:

```
Listo. Cambios en N archivos (M+/M- líneas).
- <path>:<range> — <one-sentence intent>
- <path>:<range> — <one-sentence intent>
Ábrelo en hunk (surface). Escribe 'go' o feedback.
```

The preamble is the ambiguity flag. If the agent cannot honestly write
each line, that is a signal the change deserves more scrutiny — say so
explicitly: "no estoy seguro de por qué hice X, ¿revisamos juntos antes
de seguir?".

**Inline hunk notes (selective).** Leave them ONLY when:

- the decision is non-obvious (would surprise the operator reading cold), OR
- there is a race condition, ordering constraint, or migration risk, OR
- there is a follow-up the operator should know about.

Skip them for trivial diffs (renames, formatting, lockfile bumps, single-
line bug fixes with obvious intent). Use `hunk session comment apply
--stdin` for batches; one batch beats many shell calls.

### 4. Resume

Classify the operator's next message into one of four buckets BEFORE
acting. Never auto-resume; never assume.

| Bucket | Patterns (es/en) | Action |
|---|---|---|
| **approve** | go, ok, dale, sigue, procede, ship, lgtm, ✓, +1, continue, adelante, confirmado, approved | next step (commit, push, hand back) |
| **feedback** | any other instruction-shaped message ("change X to Y", "this is wrong", "use approach Z") | iterate on the change; re-pause at the end |
| **stop** | cancel, abort, rollback, para, deten, stop, halt, revert, deshaz | revert (git restore) + acknowledge |
| **ambiguous** | doesn't match any bucket AND isn't feedback-shaped ("hmm", "ok idk", "?") | FLAG: "interpreté X como Y, ¿procedo? si no, ¿qué querías decir?" |

The flag is non-negotiable. When in doubt, ask. The cost of asking is one
chat turn; the cost of guessing wrong on a destructive operation is the
working tree.

## Prerequisite: hunk is installed

```bash
command -v hunk >/dev/null 2>&1 || {
  echo "hunk not installed. Install: brew install hunk  (or  npm i -g hunkdiff)"
  exit 1
}
hunk --version
```

If missing, fall back to printing `git diff` in the chat and asking "go?".
Do not silently skip the pause just because hunk is absent.

## Workflow A — keyword pause

```
operator: "implement X, then we'll review"
  ↓
agent: implements X
  ↓
agent: detects keyword "review" in operator's message
  ↓
agent: picks surface (cmux → herdr → manual)
  ↓
agent: prints preamble in chat
  ↓
agent: opens hunk in chosen surface
  ↓
agent: `hunk session list --json` to verify alive
  ↓
agent: leaves inline notes (selective)
  ↓
agent: waits for operator's next message
  ↓
operator: "go"  →  approve  →  next step
operator: "rename Y to Z"  →  feedback  →  iterate, re-pause
operator: "aborta"  →  stop  →  revert + ack
operator: "hmm"  →  ambiguous  →  flag, ask
```

## Workflow B — risk-aware auto-pause

The operator never said anything. The change crossed a risk threshold.
The agent MUST pause and explain why.

```
agent: finishes change
  ↓
agent: evaluates risk threshold (lines, files, paths, deps, reverts)
  ↓
threshold crossed?
  ↓ yes
agent: prints preamble WITH the reason: "Pausé porque: cruza umbral
        (5 archivos, paths en src/auth/*). Revisa antes de seguir."
  ↓
[continue with Workflow A from "picks surface" step]
```

The agent MUST surface the reason. Silent auto-pauses erode trust; the
operator needs to know which threshold fired and why.

## Workflow C — surface selection (concrete)

Pseudocode; concrete commands live in `references/surfaces.md`.

```
if command -v cmux >/dev/null 2>&1 && cmux session marker present:
    surface = "cmux"
elif test "${HERDR_ENV:-}" = 1:
    surface = "herdr"
else:
    surface = "manual"

# cmux and herdr each have their own skill. Load the matching one
# transiently for the actual pane-open command. Do NOT inline cmux/herdr
# CLI calls in this skill — that is the other skill's job.

# After opening hunk in the surface, verify the session broker registered:
hunk session list --json
# expect at least one session whose `repo` matches the current cwd
```

## Workflow D — resume classification

```python
def classify(message: str) -> str:
    msg = message.lower().strip()
    if msg in APPROVE_LEXICON:
        return "approve"
    if msg in STOP_LEXICON:
        return "stop"
    if looks_like_instruction(msg):
        return "feedback"
    return "ambiguous"  # MUST flag, never guess
```

`APPROVE_LEXICON`, `STOP_LEXICON`, and `looks_like_instruction` are
defined exhaustively in `references/lexicon.md` (es/en, case-insensitive,
trimmed). The agent MUST consult them on every pause. When the classifier
returns `ambiguous`, the agent prints:

```
Interpreté "<original message>" como ambiguo. ¿Querías decir:
  a) aprobar y seguir
  b) darme feedback específico
  c) abortar
?
```

…and waits. No state changes until the operator clarifies.

## When to stop

- Pause happened, operator gave a clear bucket, agent acted on it.
- For `approve`: next step (commit/push/hand-back) is observable in the
  terminal — never claim a commit landed from the launch command alone.
- For `feedback`: re-paused at the end of the iteration.
- For `stop`: working tree is clean (or back to the pre-change state) AND
  the agent has acknowledged.
- For `ambiguous`: agent has flagged and is waiting — no action taken.

## Boundaries

**MUST**
- Gate on `command -v hunk` before any hunk call. If missing, fall back
  to `git diff` in chat and ask.
- Evaluate all four decision points (trigger, surface, annotate, resume)
  on every potential pause moment. Never skip one.
- Print the chat preamble BEFORE pausing. The preamble is the operator's
  map; no preamble = no review.
- Classify the operator's next message into approve / feedback / stop /
  ambiguous on every pause. Never auto-resume.
- Flag ambiguity explicitly. Ask. Don't guess.
- Verify the hunk session broker registered the session before claiming
  "ready for review" (`hunk session list --json`).
- Load the bundled hunk-review skill transiently via `hunk skill path`
  for the actual CLI mechanics. Do not duplicate the hunk session API in
  this skill.
- Load the surface skill (cmux or herdr) transiently for the actual
  pane-open command. Do not inline cmux/herdr CLI calls here.
- Annotate selectively. Inline notes are for non-obvious decisions,
  risks, and follow-ups — never for diffs that explain themselves.
- Surface the reason for a risk-aware auto-pause. Silent auto-pauses
  erode trust.

**MUST NOT**
- Never run `hunk diff`, `hunk show`, `hunk patch`, `hunk pager`, or
  `hunk difftool` directly from the agent. Those are user-facing TUI
  commands. The agent's only hunk CLI is `hunk session *` and `hunk
  skill path`.
- Never auto-resume without an explicit operator signal. No timers, no
  heuristics, no "5 minutes is enough".
- Never silently skip the preamble. Even on a one-line fix, print
  something: "Cambié 1 línea en X: <intent>."
- Never write inline notes that rephrase what the code already says.
- Never modify hunk itself, ship patches upstream, or vendor hunk's
  source into this skill.
- Never name a specific harness, model, or internal tool in the body
  of this skill (per the agent-skills constitution §9). The skill
  expresses behavior; the adapter maps behavior to tools.

## References

| File | When to load |
|------|--------------|
| `references/surfaces.md` | Concrete surface selection: cmux vs herdr vs manual detection, what command to run, what to do if the chosen surface fails to register a hunk session |
| `references/lexicon.md` | Exhaustive approve / stop word lists (es/en, case-insensitive), the `looks_like_instruction` heuristic, and the exact ambiguity-flag text |
| `references/risk-thresholds.md` | Default thresholds with examples, how to override via `~/.config/agent-skills/use-hunk.toml`, the "auto" override per request |
| `references/hunk-cli.md` | Minimal hunk session API surface that this skill actually calls (subset of the bundled hunk-review skill, distilled for orchestration reference only — do not vendor) |

Authoritative external sources:

- `hunk --help`, `hunk session --help`, `hunk skill path` — bundled with the
  installed binary, always the source of truth for the CLI
- https://hunk.dev/ — product site
- https://github.com/modem-dev/hunk — source repo, `docs/agent-workflows.md`
  is the canonical agent-integration reference
- `hunk skill path` — the skill file hunk itself ships for agent-side
  mechanics; load it transiently, never duplicate
