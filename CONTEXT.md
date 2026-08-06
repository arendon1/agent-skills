# CONTEXT — Ubiquitous Language

Canonical glossary for the `agent-skills` repo. Any term used in plan
artifacts, code, or docs MUST appear here (or in a more specific entry).
Fuzzy terms are sharpened; synonyms are consolidated into a single
canonical entry.

Rules:
- This file is a glossary ONLY. It is not a spec, design pad, or
  implementation log.
- Every term carries an "_Avoid_:" line with discarded synonyms.
- Changes here reflect crystallized consensus, not individual opinions.

## sync_plan

Declarative JSON artifact produced by `cli_clickup.py` that the agent
applies with `use-clickup`. Contains `to_create` / `to_update` /
`to_archive` / `unresolved`. NOT executed directly — the agent reads
it and orchestrates.

_Avoid_: "clickup delta", "clickup patch", "task list"

## delta

Difference between the current state of Moodle (source of truth) and
the current state of ClickUp, expressed as a `sync_plan`. Computed by
`cli_clickup.py`; applied by the agent.

_Avoid_: "pending changes", "diff", "patch list"

## agent-orchestrator

Entity (human or AI agent) that decides when to run `cli_estado.py`,
`cli_calificaciones.py`, `cli_clickup.py`, and `use-clickup`. It is not
a script — it is the policy layer.

_Avoid_: "the model", "the script", "the orchestrator"

## flow-direction

Architectural rule: data flows Moodle → Local → ClickUp, never the
other way. Reclassifications go as `to_update` of the same `task_id`;
deletions from Moodle go as `to_archive`, NOT `to_delete`.

_Avoid_: "bidirectional sync", "clickup as source", "reorganize"

## frontier

In a grilling interview: every decision whose prerequisites are all settled —
the questions askable NOW without guessing answers not yet heard. The whole
frontier is asked in one round (numbered, recommended answer each), then
recomputed from the answers. Empty frontier = interview done.

_Avoid_: "next question", "pending questions", "open questions"

## grilling

The interview primitive (process layer, auto): design tree + frontier rounds +
facts-are-the-agent's-job. Owns no artifacts. Invoked by loops that must
sharpen an idea by conversation (`grill`, `triage`, `deepen`).

_Avoid_: "interviewing", "questioning", "interrogation"

## hunk review pause

A point in the agent loop where the agent stops, prints a chat
preamble, opens `hunk` (modem-dev) in the active terminal multiplexer
(cmux preferred, then herdr, then manual fallback), and waits for the
operator's next message. The pause is triggered by an explicit operator
keyword OR a risk threshold (>= 80 lines, >= 4 files, sensitive paths,
new dependency, revert). The operator resumes with an `approve` /
`feedback` / `stop` / `ambiguous` message; the agent never auto-resumes.

_Avoid_: "code review", "diff review", "agent handoff", "wait for human"

## resume bucket

Classification of the operator's next message after a hunk review
pause. Exactly one of four:

- **approve** — go, ok, dale, ship, lgtm, etc. → next step
- **feedback** — instruction-shaped message → iterate + re-pause
- **stop** — cancel, abort, rollback, para, etc. → revert + ack
- **ambiguous** — anything else → flag and ask, no state change

Precedence: question > instruction > stop > approve > ambiguous.
Questions and instructions beat stop/approve so the agent never
mistakes a question for an order, and never mistakes a precise change
request for a generic stop. See `domain/use-hunk/references/lexicon.md`
for the algorithm and `scripts/test_classifier.py` for the 30 cases.

_Avoid_: "approval", "rejection", "go signal", "user response"

## preamble

The 2–3 line chat summary the agent prints when pausing for a hunk
review. Lists what changed (paths + line ranges + one-sentence intent)
and what surface to open. The preamble is also the implicit ambiguity
flag: if the agent cannot honestly write each line, the change deserves
more scrutiny.

_Avoid_: "summary", "diff header", "commit message"

## trigger override

An operator word (`auto`, `skip-review`, `no-review`, `autonomo`,
`autónomo`, `without review`, `sin revisión`, `sin revisar`) that
tells the agent to skip the next pause. Per-request, not per-session.
If the word arrives AFTER a pause already happened, the classifier
treats it as `ambiguous` (the operator is supposed to have reviewed;
"auto" mid-review is a sign of confusion, ask before acting).

_Avoid_: "skip flag", "auto mode", "review toggle"

## general list

Default list in the Agent Ops space for all agent-tracked work without a
dedicated home. Statuses encode the pipeline; the list itself is not a state.

_Avoid_: "Agent Tasks", "task bucket", "inbox list"

## status-as-state

Rule: a task's ClickUp status is the ONLY state machine (`to do` → `ready` →
`in progress` → `review` → `blocked` → `complete`). Progress never lives in
lists, tags, or comments alone.

_Avoid_: "list as status", "phase as list", "kanban column"

## list-as-project

Rule: a list exists only to enclose a big named project or goal (a cluster of
~5+ related tasks). Lists are never created for status, phase, or priority.

_Avoid_: "status list", "sprint list", "priority board"

## scoping gate

Rule: no non-trivial work starts until it exists as a task in Agent Ops
(`to do`/`ready`). Work without a task is out of scope until registered.

_Avoid_: "rogue work", "unscoped build", "shadow task"

## owner claim

Recording which agent works a task: the `Owner` custom field (value
`<harness>@<device>`, e.g. `pi@macbook-pro`) mirrored as the first line of the
task description `Owner: <identity>` + start comment. The Owner record is the
collision signal — claimed work is worked only by its owner.

_Avoid_: "assignee", "taker", "responsible"

## identity tags

Every task carries two tags naming who created/owns it: `harness:<name>`
(the runtime the agent runs as) and `device:<name>` (the physical machine,
operator's alias or hostname). Set at creation; tags must pre-exist in the
space. They make "what is running on the phone" answerable per device/harness.

_Avoid_: "origin tag", "source tag", "routing tag"

## waiting-on-andres

Tag for tasks that need the operator's decision or input; the highest-value
query at session start.

_Avoid_: "blocked-on-human", "needs-input", "ping-andres"
