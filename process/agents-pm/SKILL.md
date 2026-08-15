---
name: agents-pm
description: |
  Agent project management over the shared ClickUp **Agents** space: keep every
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
  version: "2.0.0"
---

# agents-pm

Cross-device project management for a team of agents, backed by the shared ClickUp
**Agents** space. One pipeline, one source of truth, visible to everyone. This skill
defines the conventions; the `use-clickup` skill (domain, provides `clickup-api`) is the
transport. **Version 2 (2026-08-15): rebuilt from scratch after a full API audit** — the
space, statuses, and tags are new; the Owner field, identity tags, and process tags are
gone (see `references/schema.md`).

## WHEN (self-trigger)

- Session start / after context compaction — read the space before asserting anything
  about the team's work.
- Before starting ANY non-trivial work — check for an existing task, scope it if missing.
- Claiming, updating, blocking, reviewing, or closing a tracked task.
- Asked "what is the team working on", "who owns X", "is anything blocked",
  "what is running on device X".
- Suspicion of duplicate or out-of-scope work.

## PREREQUISITE

Load the `use-clickup` skill before running any command. All API calls go through its
client and scripts (audited 2026-08-15 — see its references for verified behavior).

## STEP 0 — READ THE SPACE (session start, after compaction)

Query the General list before asserting anything about team state. Never answer from
memory. Group results:

1. Open tasks by status — `backlog` (queued), `to do` (released, awaiting claim),
   `in progress` (claimed — who?), `blocked` (stuck — read the blocker comment),
   `review` (awaiting Andrés's accept — surface first).
2. Work-type tags (research/build/analysis/…) — the lanes.
3. The "needs Andrés" queue is simply the status filter `review` + `blocked`.

## STEP 1 — SCOPE BEFORE WORK (scoping gate)

No non-trivial work starts unless it already exists as a task.

1. Search the space for an existing task (team query `GET /team/{id}/task` + client-side
   keyword match — **global text search does not exist**).
2. Found + unclaimed → proceed to STEP 2.
3. Found + claimed by another hand (claim comment present) → do NOT start; flag overlap.
4. Not found → create the task in `backlog` FIRST, self-contained description, with its
   work-type tags, then claim it.

## STEP 2 — CLAIM

1. Status → `in progress`.
2. Post the claim comment: `Claimed by <hand> — <what I'll deliver>`.
3. Re-read the task; if another hand's claim comment appeared, release (back to `to do`).
4. Multi-step ticket? Add **subtasks** — they're the progress bar (Andrés's ask).

## STEP 3 — UPDATE (progress)

On every meaningful milestone: refresh the description (self-contained), append to
`## Evidence Log`, add an evidence comment. Move status only when state actually changes.

## STEP 4 — BLOCK

1. Status → `blocked`.
2. Comment the blocker precisely (what, why, who/what unblocks it).
3. If Andrés must act, he'll see it via the `blocked` status — no tag needed.

## STEP 5 — REVIEW

Done → status → `review` + fill `## Proof of work`. **Only Andrés moves `review` →
`complete`** (the accept gate; never skipped).

## STEP 6 — COMPLETE

Andrés accepts → status `complete` (closes). Closed tasks are the archive; query with
`include_closed=true`. Note: `statuses[]=complete` returns closed tasks even without
the flag.

## STATUS PIPELINE (exact lowercase — ClickUp normalizes to lowercase on write)

`backlog` → `to do` → `in progress` → `blocked` → `review` → `complete`

| Status | Meaning | Set by |
|---|---|---|
| `backlog` | idea dump, not started | creator (Andrés / phone-pi) |
| `to do` | RELEASED — Andrés's GO; awaiting claim | **only Andrés** |
| `in progress` | being worked; claimed via comment | the worker |
| `blocked` | cannot proceed; blocker in comment | the worker |
| `review` | awaiting Andrés's accept | the worker |
| `complete` | accepted; closes the task | **only Andrés** |

Statuses are the ONLY state machine. Never encode progress in a list.

## TAGS — WORK-TYPE FACETS (mix-and-match, no process tags)

| Tag | Meaning | Example |
|---|---|---|
| `research` | explore, discover, learn | "is X worth doing?" |
| `build` | create something | code, projects, artifacts |
| `analysis` | evaluate, compare, data work | model reviews, cost analysis |
| `report` | a document to be read | papers, reports |
| `university` | university work | courses, Moodle, papers |
| `business` | professional lane | job search, compensation |
| `personal` | life — wife, home, errands | "something for my wife" |
| `infrastructure` | devices, environment, tooling | phone/tablet upkeep |
| `automation` | bots, syncs, schedulers | daemons, webhook/poller |
| `design` | UI/UX, architecture, visuals | prototypes, diagrams |
| `writing` | language craft | copy, editing, newsletters |
| `finance` | money work | transactions, budgets |
| `content` | produced media | posts, videos, images |
| `learning` | skill-building, study | teach sessions, courses |

Rules: **full words only** (never `uni`/`infra` — Andrés's directive); any combination,
zero to a few per task; tags are created at space level and registered here. No
`waiting-on-andres` (review/blocked cover it), no `future` (backlog covers it), no `skill`
(research covers it), no identity tags (the claim comment carries identity).

## LISTS

- **General** — default list; all agent-tracked work without a dedicated home.
  ID in `references/schema.md`.
- A list exists ONLY to enclose a big named project (~5+ related tasks). New lists are
  registered in `references/schema.md`.

## CUSTOM FIELDS — NONE

Custom fields are blocked on the Free plan (`FIELD_605`) and the design deliberately uses
zero. Identity = the claim comment. There is no Owner field.

## DOCS — BANNED

ClickUp Docs are permanent by design (undeletable, even in the UI) — **core directive
(Andrés): never create Docs.** Long-form artifacts are local files; tasks link paths and
stay fully self-contained (device-death safe).

## WHEN TO STOP

- Task registered, claimed, updated, blocked, or closed, each with evidence.
- Space state re-read before any state assertion.
- No work started that had no task.

## BOUNDARIES

MUST:

- Statuses encode progress; lists enclose projects. Never invert.
- Create the task before starting non-trivial work (scoping gate).
- Claim before working: status `in progress` + claim comment.
- Tag every task with its work-type facets at creation.
- Keep descriptions self-contained and current (Evidence Log).
- Comment evidence at every transition.
- Re-read the space at session start and before each new work item.
- Use `include_closed=true` when querying.
- Match status strings exactly (lowercase).
- Respect the shared rate limit (~100/min per key across devices).

MUST NOT:

- Put secrets in task content (shared space).
- Duplicate existing work — search first.
- Cache task state across sessions; the space is the sole source of truth.
- Start work claimed by another hand without resolving the overlap.
- Create ClickUp Docs (banned).
- Set `to do` (Andrés's GO column) — only Andrés releases work.

## REFERENCES

| File | Covers |
|---|---|
| `references/schema.md` | Canonical Agents space schema: IDs, statuses, tags, description contract |
| `references/workflows.md` | Exact commands per step, agent identity, pitfalls |
