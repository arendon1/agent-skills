# HANDOFF — agent-skills architecture refactor

> For a fresh agent picking up the agent-skills skill-system redesign.
> Read this fully, then open `agent-skills/architecture-plan.html` for the full spec.

## goal

Refactor `~/Documents/Projects/agent-skills/` from a flat collection of independent skills into a **cohesive, self-triggering skill system** that merges
the best mechanisms from four source skill ecosystems into one agnostic
architecture, constrained by the user's own rules (agnosticism, language,
right-size).

The user develops their own skills here, derived from / inspired by external skill
ecosystems. This redesign is the architecture for that collection.

## current state (READ CAREFULLY)

- **`agent-skills/` was reset to its base** after interrupted work created a failed
  repo state. The base = the original 10 skills + the original `AGENTS.md` + the
  user's `progress.md`. Git HEAD is `7a16d9d refactor: rename analyze-llm-model to
  analyze-model`.
- **ALL implementation from the prior session was lost in the reset:**
  - The rewritten `AGENTS.md` constitution — GONE (old one is back).
  - 21 new skills (`caveman`, `lessons`, `tdd`, `debug`, `verify`, `deepen`,
    `domain-modeling`, `git`, `dispatch`, `bootstrap`, `grill`, `design`, `spec`,
    `plan`, `build`, `research`, `review`, `check`, `prototype`, `handoff`,
    `skill-find`, `skill-add`, `teach`, `triage`) — GONE.
  - The Layer 4 pi adapter (`.pi/extensions/agent-skills.ts`) and `package.json` — GONE.
  - The upgraded `skill-forge` audit/init scripts — reverted to originals.
  - Domain-skill frontmatter migrations — reverted.
  - `git-master` removal — reverted (it's back; it's superseded by the planned
    merged `git` skill).
- **What survived:** `agent-skills/architecture-plan.html` — the full design spec
  and locked decisions. This is the source of truth for the architecture.

So: the design is done and captured in `architecture-plan.html`. The
implementation needs to be redone from the base, following that plan. Do NOT
re-litigate the design — it's locked. Implement it.

## the source of truth

**`agent-skills/architecture-plan.html`** — open it in a browser or read the HTML.
It contains:
- Executive summary + design principles
- Triggering model (`auto` / `user` / `bootstrap`)
- Memory vs artifacts framing (Soul Protocol is OUT OF SCOPE)
- Per-plan artifact structure (`/docs/plans/<yyyy-mm-dd>-<type>-<slug>/`)
- Ubiquitous language as first-class cross-cutting concern (`CONTEXT.md`)
- Layer architecture (process / domain / utility + Layer 4 adapters)
- Full skill catalog (31 skills: 14 loops + 12 disciplines + utility + bootstrap)
- `caveman` compression spec (full symbol/emoji/grammar tables)
- Agnosticism rules
- Overlap map (~57 source skills → 31 merged)
- Rollout plan
- 10 locked decisions

A live HTTP server may still be serving it at `http://localhost:8765/architecture-plan.html`
(check with `curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/architecture-plan.html`;
if not running, start one: `cd agent-skills && python3 -m http.server 8765 &`).

## the four source ecosystems (siblings in the workspace)

Read these to understand the mechanisms being merged. Do NOT copy them wholesale —
the point is to derive agnostic versions.

| Repo | Path | Steal |
|---|---|---|
| **Cavekit** | `~/Documents/Projects/cavekit/` | `caveman` compression grammar (toned — see plan); sectioned ownership; backprop → `lessons`; right-size; per-plan folders |
| **Superpowers** | `~/Documents/Projects/superpowers/` | bootstrap auto-trigger concept (agnosticized); rationalization tables (selective); TDD Iron Law; `.pi/extensions/superpowers.ts` is the reference for the adapter |
| **Matt Pocock skills** | `~/Documents/Projects/skills/` | user/model invocation split → 3-value `invocation`; grilling pattern → `grill`; `CONTEXT.md` ubiquitous language; vertical slices; `domain-modeling` skill |
| **Soul Protocol** | `~/Documents/Projects/soul-protocol/` | OUT OF SCOPE for this skills redesign. It's existing infra the user has. Skills must NOT depend on it. |

## the 10 locked decisions (do not re-litigate)

1. **Artifact path:** `/docs/plans/<yyyy-mm-dd>-<type>-<slug>/` with `PRD.md`,
   `ARD.md`, `SPEC.md`, `PLAN.md`, `LESSONS.md` inside (created lazily, right-sized).
2. **Markdown artifacts** (NOT HTML). HTML only when the user asks for it ad-hoc.
3. **Memory vs artifacts:** agent memory (system prompt / Soul) is remembrance;
   project artifacts are docs the agent must remember to check/update. Soul is
   out of scope.
4. **Ubiquitous language** is a first-class cross-cutting concern: `CONTEXT.md` at
   repo root; every skill reads it; `domain-modeling` maintains it.
5. **`caveman`** keeps its name; symbols limited to programming operators
   (`-> => >= <= != == && || ! in not in := ~`), RFC 2119 (`MUST NEVER SHOULD MAY`),
   ranges (`1..* 0..1`), `§`; traffic-light emoji 🟢🟡🔴🔵 + 🚧 WIP + directional
   ⬆️⬇️↗️↘️↔️ for CHAT ONLY; ASCII words (`PASS FAIL WARN INFO BLOCK HARDEN WIP NEVER`)
   in artifacts; obscure math (`∀ ∃ ∴ ⊥`) dropped; `[x]`/`[ ]` TODO-checkbox only.
6. **Triggering:** 3-value `auto` (default) / `user` (must declare `loop` +
   `deliverable`) / `bootstrap` (only the `bootstrap` skill).
7. **Layers:** `process` / `domain` / `utility`. Process may call all; domain may
   call domain+utility NEVER process; utility is leaf.
8. **Pipeline:** PRD → ARD → Spec → Plan → Tasks/Tests → Review.
9. **`research` → `research-literature`:** the generic `research` loop delegates to
   domain capabilities by `provides` field (e.g. `research-literature`
   `provides: [academic-search]`).
10. **Soul out of scope.** Domain skills preserved (frontmatter-only migration).
    `teach` and `triage` kept as optional loops.

## the architecture (summary)

**Layers:**
- Layer 4 — adapters (`adapters/pi/`, `adapters/opencode/`). The ONLY place
  harness coupling lives. For pi: a `.pi/extensions/agent-skills.ts` that does
  `resources_discover` (register skills) + `session_start`/`session_compact`
  (re-inject bootstrap) + `context` (inject bootstrap body). Reference impl:
  `superpowers/.pi/extensions/superpowers.ts`.
- Layer 3 — utility: `skill-forge`, `skill-find`, `skill-add`, `caveman`, `oracle`,
  `scout`, `bootstrap`.
- Layer 2 — domain: `use-clickup`, `research-literature`, `make-a-diagram`
  (capabilities, `auto`); `gestionar-cursos`, `generar-paper`, `analyze-model`
  (loops, `user`).
- Layer 1 — process: loops (`grill design spec plan build research review check
  prototype handoff teach triage`) + disciplines (`tdd debug verify lessons deepen
  domain-modeling git dispatch`).
- Layer 0 — constitution: `AGENTS.md` + `skill-forge` (the enforcer).

**Frontmatter schema (AGENTS.md §F):**
```yaml
---
name: lowercase-hyphens
description: |
  What it does, briefly.
  Use when [specific triggers].   # REQUIRED — "Use when" literal
invocation: auto          # auto | user | bootstrap
layer: process            # process | domain | utility
loop: <name>              # required if invocation: user
deliverable: <thing>      # required if invocation: user
provides: [capability]    # required if layer: domain (warning if missing)
metadata:
  version: "1.0.0"
---
```

**Agnosticism (§A0 golden rule):** skills express behavior, NEVER tools. No harness
names (`pi`, `OpenCode`, `Claude Code`, `Cursor`, `Antigravity`), no tool names
(`Skill`, `Task`, `subagent`, `TodoWrite`, `soul_recall`), no slash-command syntax
in bodies. The adapter maps behavior → tool.

**`skill-forge audit`** enforces all of this (§F/§T/§L/§A0) with pass/fail exit
codes. It MUST be upgraded from the current prompt-output style to direct
validation. Reference: the prior session built a working `audit.py` — re-implement
from the plan + the patterns below.

## rollout order (follow this; nothing breaks between steps)

1. **Constitution** — rewrite `AGENTS.md` with the full schema, layers, triggering,
   per-plan artifacts, ubiquitous-language rules, caveman rules, agnosticism,
   memory-vs-artifacts. (Plan §decisions + §layers + §caveman + §agnosticism.)
2. **`caveman` skill** — small, self-contained. Full spec in the plan's caveman
   section.
3. **`lessons` skill** — bug → `LESSONS.md` reflex (6-step protocol).
4. **`skill-forge` upgrade** — `init.py` (new frontmatter scaffold) + `audit.py`
   (direct pass/fail enforcer of §F/§T/§L/§A0). The audit MUST catch: missing
   `invocation`/`layer`, `user` skills without `loop`/`deliverable`, harness/tool
   names in body, missing "Use when" in description, >500 lines.
5. **Process skills** — build one at a time. Order of pain recommended: `grill`,
   `plan`, `build`, `debug`, `verify`, `review`, `check`, then the rest.
6. **Migrate existing domain skills** — frontmatter-only (add `invocation`,
   `layer`, `provides`, `loop`/`deliverable`). No logic rewrites. Remove
   `git-master` (superseded by the merged `git` skill).
7. **Adapter (Layer 4)** — `.pi/extensions/agent-skills.ts` + `package.json`.
   Test with `pi -e /path/to/agent-skills -p "List the skill names you have..."`.

## implementation strategy (do this, don't just build all 31 at once)

The prior session built everything in one pass and it got lost. The robust approach
is a **vertical slice**: pick a REAL objective the user is about to work on, and
build only the skills that slice needs (grill + plan + build + tdd + verify + git +
lessons + caveman + domain-modeling ≈ 9 skills). Run the objective through them
end-to-end, producing a complete `/docs/plans/<date>-<type>-<slug>/` folder. If the
slice works in a live session, the architecture is proven — then scale horizontally
to fill in the rest.

If the user prefers "build everything then refine," that's valid too — the prior
session did exactly that and it worked (30/31 passed audit before the reset). Just
be aware it's more to lose if interrupted. Commit after EACH skill passes audit.

## verification

Every skill MUST pass `python3 skill-forge/scripts/audit.py <name>` (exit 0).
Run the whole catalog after building:
```bash
cd agent-skills && for d in */; do s="${d%/}"; [ -f "$d/SKILL.md" ] && python3 skill-forge/scripts/audit.py "$s"; done
```
Target: all PASS except known refinements (e.g. `analyze-model` reads OpenCode's
SQLite usage DB as a data source — that's legitimate domain integration, not
runtime coupling; the audit's blunt scan flags it; refine the audit or the skill
body wording).

## key conventions to keep straight

- **Caveman applies to artifacts** (`PRD.md`, `ARD.md`, `SPEC.md`, `PLAN.md`,
  `LESSONS.md`, `RESEARCH.md`, `CONTEXT.md`), NOT to code, commits, user-facing
  explanations, or chat-to-the-human (normal English there; emoji allowed in chat
  for status/severity per the traffic-light palette).
- **Sectioned ownership:** each loop owns specific artifacts. `build` only flips
  `PLAN.md` task status cells — it MUST NOT rewrite other artifacts. `lessons`
  owns `LESSONS.md` + the invariant section of `ARD.md`/`SPEC.md`. etc.
- **Per-plan folders, not one global spec.** Each objective (fix/feature/spike/
  refactor) gets `docs/plans/<yyyy-mm-dd>-<type>-<slug>/`. `CONTEXT.md` is shared
  at repo root across all plans.
- **`bootstrap` is the only `bootstrap`-invoked skill**, and it couples ONLY
  through the adapter (injected by the adapter, not by referencing a harness).
- **Soul Protocol: do not depend on it.** Skills degrade gracefully to file-only.

## pre-existing user tasks (from agent-skills/progress.md)

These predate the redesign and are about `analyze-model` (the LLM cost/quality
eval skill) and subagent model routing. They are NOT part of the architecture
refactor but the user still has them open. Surface them, don't silently drop:
- P0: rename source repo `analyze-llm-model/` → `analyze-model/` (drift between
  source and deployed copy).
- P1: M3 model rollout phasing + calibration (oracle/planner/reviewer subagents).
- P2: `forecast.py` regression, Obsidian chart y-axes, subagent cost attribution.

The redesign's frontmatter migration of `analyze-model` (`invocation: user`,
`layer: domain`, `loop: analyze-model`, `deliverable: model cost/quality eval
report`, `provides: [model-analysis]`) is separate from these and should not
block them.

## pointers

- `agent-skills/architecture-plan.html` — the full design (READ THIS).
- `agent-skills/AGENTS.md` — currently the OLD constitution; will be rewritten in
  rollout step 1.
- `agent-skills/progress.md` — the user's pre-existing task tracker.
- `cavekit/FORMAT.md` + `cavekit/skills/caveman/SKILL.md` — the original caveman
  spec to tone down.
- `cavekit/skills/{spec,build,check,grill,research,review,deepen,backprop}/SKILL.md`
  — the per-plan SDD loop skills to derive from.
- `superpowers/skills/{brainstorming,test-driven-development,systematic-debugging,
  using-superpowers,writing-skills}/SKILL.md` — superpowers mechanisms to merge.
- `superpowers/.pi/extensions/superpowers.ts` — the reference pi adapter
  implementation. Copy its structure, swap the bootstrap skill path and marker.
- `superpowers/.opencode/plugins/superpowers.js` + `INSTALL.md` — the reference
  OpenCode adapter (for the optional second adapter).
- `skills/skills/{productivity/grilling,engineering/grill-with-docs,engineering/
  domain-modeling,engineering/tdd,engineering/diagnosing-bugs}/SKILL.md` — Matt
  Pocock's mechanisms to merge (grilling core, domain-modeling, vertical-slice
  tdd, feedback-loop-first debugging).

## what "done" looks like

- `AGENTS.md` rewritten as the constitution.
- `caveman` + `lessons` + upgraded `skill-forge` exist and pass audit.
- All process/domain/utility skills exist and pass `skill-forge audit` (target
  30+/31 PASS).
- The Layer 4 pi adapter exists; `pi -e <repo> -p "List the skill names..."` shows
  all 31 skills discovered.
- (Optional) OpenCode adapter.
- At least one real objective run end-to-end through grill→plan→build→lessons,
  producing a complete `docs/plans/<date>-<type>-<slug>/` folder.

## one-line next step

Read `agent-skills/architecture-plan.html`, then start rollout step 1: rewrite
`agent-skills/AGENTS.md` as the constitution. Confirm with the user before each
rollout step if they want checkpoints, or build straight through if they say so.
