---
name: agents-pm
description: |
  Agent project management over the shared ClickUp Agent Ops space: keep every
  agent's work visible, scoped, claimed, and non-overlapping across devices and
  harnesses. Statuses drive progress; lists enclose big named projects or goals.
  Use when starting a session or after context compaction, before picking up any
  non-trivial work, to check what other agents are doing, to register new work
  before it starts (nothing is built outside scope), to claim, update, block,
  review, or close a tracked task, or when asked about the state of the team's work.
invocation: auto
layer: process
language: en-US
metadata:
  version: "1.0.0"
---

# agents-pm

Cross-device project management for a team of agents, backed by the shared
ClickUp **Agent Ops** space. One pipeline, one source of truth, visible to
everyone. This skill defines the conventions; the `use-clickup` skill
(domain, provides `clickup-api`) is the transport.

## WHEN (self-trigger)

- Session start / after context compaction — read the space before asserting
  anything about the team's work.
- Before starting ANY non-trivial work — check for an existing task, scope it
  if missing.
- Claiming, updating, blocking, reviewing, or closing a tracked task.
- Asked "what is the team working on", "who owns X", "is anything blocked",
  "what is running on device X", "which harness produced this".
- Suspicion of duplicate or out-of-scope work.

## OWNERSHIP

Owns the Agent Ops conventions: the status pipeline, the list-as-project rule,
the task lifecycle, and the read-side habit. Handles task state ONLY through
the `use-clickup` skill. Does not duplicate ClickUp API knowledge.

## PREREQUISITE

Load the `use-clickup` skill (provides `clickup-api`) before running any
command in this skill. All API calls go through its client and scripts. The
ClickUp API key must be available to that skill (its auth resolution covers
`.env` and the `CLICKUP_API_KEY` environment variable).

## STEP 0 — READ THE SPACE (session start, after compaction)

Query the General list before asserting anything about team state. Never
answer from memory. Run the search-task script of the `use-clickup` skill
(see `references/workflows.md` for exact commands) and group results:

1. Open tasks by status — what is queued (`to do`, `ready`), in flight
   (`in progress`), awaiting review (`review`), or stuck (`blocked`).
2. Tasks tagged `waiting-on-andres` — surface these to the operator first.
3. Who owns each in-progress/review task — Owner field + `Owner:` line in the
   description; group in-flight work by device and harness (identity tags).

## STEP 1 — SCOPE BEFORE WORK (scoping gate)

No non-trivial work starts unless it already exists as a task.

1. Search the space for an existing task covering the work (by name keywords,
   workspace-wide, including closed).
2. Found + unclaimed → proceed to STEP 2.
3. Found + claimed by another agent → do NOT start; flag the overlap.
4. Not found → create the task in `to do` FIRST, with a self-contained
   description (objective, context pointers, verified facts, explicit next
   steps), then claim it.

## STEP 2 — CLAIM

1. Set status to `in progress`.
2. Record the owner: set the Owner custom field (value `<harness>@<device>`)
   and mirror it as the first line of the task description
   `Owner: <harness>@<device>`.
3. Ensure the task carries the `harness:<name>` and `device:<name>` tags
   (add them via the task-tag endpoint if missing — see references).
4. Add a comment: started, what will be delivered, ETA if any.

## STEP 3 — UPDATE (progress)

On every meaningful milestone:

1. Refresh the description so it stays self-contained — a cold agent must be
   able to resume from it alone.
2. Add a comment with evidence (verified facts, links, results).
3. Move the status only when the actual state changes.

## STEP 4 — BLOCK

1. Status → `blocked`.
2. Comment the blocker precisely (what, why, what unblocks it).
3. If the operator must act: add the tag `waiting-on-andres`.

## STEP 5 — REVIEW

Work that needs a review pass goes to `review` (NOT `blocked` — blocked means
cannot proceed). Comment who reviews and what to check.

## STEP 6 — COMPLETE

Done → status `complete` (closes the task) + closing comment with evidence.
Closed tasks are the archive; query them with `include_closed=true`.

## STATUS PIPELINE

| Status | Meaning | Set by |
|---|---|---|
| `to do` | backlog, not started | creator |
| `ready` | picked for next | any agent |
| `in progress` | being worked; Owner recorded | the worker |
| `review` | awaiting a review pass | the worker |
| `blocked` | cannot proceed; blocker commented | the worker |
| `complete` | done, closed | the worker |

Statuses are the ONLY state machine. Never encode progress in a list.

## LISTS

- **General** — default list; all agent-tracked work that has no dedicated
  home. ID in `references/schema.md`.
- A list exists ONLY to enclose a big named project or goal — a cluster of
  ~5+ related tasks. Creating a list to represent status, phase, or priority
  is forbidden. New lists are recorded in `references/schema.md`.

## TAGS

| Tag | Meaning |
|---|---|
| `skill` | skill-building work |
| `future` | deferred / long-horizon |
| `infra` | environment, deployment, tooling |
| `waiting-on-andres` | needs the operator's decision/input (highest-value) |
| `harness:<name>` | runtime the agent runs as — one per task |
| `device:<name>` | physical machine (operator's alias or hostname) — one per task |

Every task carries both identity tags, set at creation by the creating agent.
They make work visible per device and per harness across the whole team.

## WHEN TO STOP

- Task registered, claimed, updated, blocked, or closed, each with evidence.
- Space state re-read before any state assertion.
- No work started that had no task.

## BOUNDARIES

MUST:

- Statuses encode progress; lists enclose projects. Never invert.
- Create the task before starting non-trivial work (scoping gate).
- Claim before working: Owner field + `Owner:` description line, value
  `<harness>@<device>`.
- Tag every task with `harness:<name>` and `device:<name>` at creation.
- Keep descriptions self-contained and current.
- Comment evidence at every transition.
- Re-read the space at session start and before each new work item.
- Use `include_closed=true` when querying.

MUST NOT:

- Put secrets in task content (shared space).
- Duplicate existing work — search first.
- Cache task state across sessions; the space is the sole source of truth.
- Start work claimed by another agent without resolving the overlap.

## REFERENCES

| File | Covers |
|---|---|
| `references/schema.md` | Canonical Agent Ops schema: IDs, statuses, tags, list evolution |
| `references/workflows.md` | Exact commands per step, agent identity, pitfalls |
