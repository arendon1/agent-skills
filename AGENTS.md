# AGENTS.md

> Constitution + runtime conventions for the **agent-skills** skill system.
> Every skill in this repo is validated against this document. `skill-forge audit`
> enforces the rules marked MUST/MUST NOT below.

A cohesive, self-triggering skill system that merges mechanisms from Cavekit
(compression, right-size, per-plan folders), Superpowers (bootstrap auto-trigger,
TDD), and Matt Pocock (3-value invocation, grilling, ubiquitous language).
Agnostic at the core: skills express behavior; the adapter maps behavior to tools.

---

## §0 PURPOSE

A collection of agent skills — each subdirectory is an independent, deployable
skill — that together form a self-triggering system: auto-triggered disciplines
(reusable substance) are invoked by user-triggered loops (entry points that
produce a named deliverable). A thin adapter layer provides session bootstrap
without coupling any skill to a specific harness.

---

## §1 PRINCIPLES

1. **Behavior triggers domain.** Process loops discover and invoke domain
   capabilities. Domain skills never invoke process skills.
2. **Self-triggering by default.** Most skills are `auto`. They fire on context,
   symptoms, or behavior. User invocation is the exception.
3. **Loops produce deliverables.** Every `user`-invoked skill MUST declare its
   `loop:` and `deliverable:`. No generic "help me" entry points.
4. **One plan per objective.** Each fix, feature, spike, or refactor gets its own
   `/docs/plans/<yyyy-mm-dd>-<type>-<slug>/` folder.
5. **Compression with clarity.** `caveman` compresses spec-adjacent prose without
   obscuring meaning. Symbols limited to programming operators + RFC 2119 + `§`.
6. **Agnostic at the core.** Skills express behavior. The adapter maps behavior
   to tools. Only the adapter knows harness-specific names. (See §9.)

---

## §2 DISCOVERY

Skills come and go. The agent MUST discover skills dynamically by scanning
the category buckets for `SKILL.md` files. NEVER hardcode a skill list — the
active set is whatever directories exist right now. Every skill lives in its
own directory under its layer's category folder: `process/`, `domain/`, or
`utility/` at the repo root (e.g. `process/grill/SKILL.md`). The adapter
(Layer 4) registers the repo root for discovery; `skill-forge audit` and
`manifest.py` resolve a skill name to its bucket (`<layer>/<name>`).

---

## §3 LAYERS

Skills are organized into layers with a strict call rule. The adapter (Layer 4)
is the only place harness-specific coupling lives.

| Layer | Name | Skills |
|---|---|---|
| 4 | Adapters | `adapters/pi/`, `adapters/opencode/` — harness coupling only |
| 3 | Utility | `skill-forge`, `caveman`, `bootstrap`, `skill-find`, `skill-add` |
| 2 | Domain | `use-clickup`, `research-literature`, `make-a-diagram`, loops (`gestionar-cursos`, `generar-paper`, `analyze-model`) |
| 1 | Process | loops (`grill design spec plan build research review check prototype handoff teach triage`) + disciplines (`tdd debug verify lessons deepen domain-modeling git dispatch`) |
| 0 | Constitution | this file + `skill-forge` (the enforcer) |

**Call rules (MUST hold):**

| Caller | May call | MUST NOT call |
|---|---|---|
| Layer 1 process | L1 disciplines, L2 domain, L3 utility | — |
| Layer 2 domain | L2 domain, L3 utility | L1 process (never inverts control) |
| Layer 3 utility | nothing (leaf skills) | L1, L2 |

---

## §4 TRIGGERING

Every skill declares `invocation:` in its frontmatter. Three values, strict
contracts:

| Value | Role | Contract |
|---|---|---|
| `auto` | Default | Self-triggers on context, symptoms, or behavior. Disciplines + most domain capabilities. |
| `user` | Loop entry only | Human invokes a named loop producing a specific deliverable. MUST declare `loop:` and `deliverable:`. |
| `bootstrap` | Session enabler | Injected at session start and after compaction. Only ONE skill holds this role: `bootstrap`. |

**Enforceable rule:** `skill-forge audit` rejects a `user`-invoked skill that does
not declare both `loop:` and `deliverable:`. This eliminates ambiguous entry
points (e.g. `grill-me` vs `brainstorming` collisions).

---

## §5 FRONTMATTER SCHEMA

```yaml
---
name: lowercase-hyphens          # REQUIRED, matches dir name
description: |
  What it does, briefly.
  Use when [specific triggers].   # REQUIRED — "Use when" literal MUST appear
invocation: auto                 # REQUIRED — auto | user | bootstrap
layer: process                  # REQUIRED — process | domain | utility
loop: <name>                     # REQUIRED if invocation: user
deliverable: <thing>             # REQUIRED if invocation: user
provides: [capability]           # REQUIRED if layer: domain (warning if missing)
language: en-US                  # OPTIONAL — en-US | es-CO; no mixing within a skill
metadata:
  version: "1.0.0"
---
```

**Field requirements (enforced by audit):**
- `name` — lowercase-hyphens, matches the skill directory name.
- `description` — MUST contain the literal phrase `Use when`.
- `invocation` + `layer` — REQUIRED on every skill.
- `loop` + `deliverable` — REQUIRED when `invocation: user`.
- `provides` — REQUIRED when `layer: domain`; lists capabilities the domain skill
  exposes (e.g. `provides: [clickup-api]`). Used by `research` to delegate to
  domain capabilities by capability (e.g. `research-literature provides:
  [academic-search]`).

---

## §6 ARTIFACTS

Each objective (fix, feature, spike, refactor) gets its own plan folder. The
folder contains the basic artifacts that comprise the development cycle.

```
repo-root/
├── CONTEXT.md                          ← shared ubiquitous language (cross-plan)
└── docs/
    └── plans/
        ├── <yyyy-mm-dd>-<type>-<slug>/
        │   ├── PRD.md
        │   ├── ARD.md
        │   ├── SPEC.md
        │   ├── PLAN.md
        │   └── LESSONS.md
        └── archive/                     ← completed plans (optional)
```

**Naming:** `/docs/plans/<yyyy-mm-dd>-<type>-<slug>/`
- `yyyy-mm-dd` — plan start date
- `type` — `fix`, `feature`, `spike`, `refactor`, `chore`, `docs`, `test`
- `slug` — short hyphenated description

**Basic artifacts:**

| Artifact | Pipeline stage | Produced by |
|---|---|---|
| `PRD.md` | Requirements | `grill` |
| `ARD.md` | Architecture design | `design` |
| `SPEC.md` | Detailed spec | `spec` |
| `PLAN.md` | Implementation plan / tasks | `plan` |
| `LESSONS.md` | Bugs / learned invariants | `lessons` (auto) |
| `RESEARCH.md` (optional) | Sourced external knowledge | `research` |

**Artifacts are created lazily. Right-size to blast radius:**

| Objective size | Artifacts created |
|---|---|
| One-line fix | `PLAN.md` only (+ `LESSONS.md` if bug) |
| Small feature | `PRD.md` + `PLAN.md` |
| Medium feature | `PRD.md` + `ARD.md` + `PLAN.md` |
| Complex / high-blast-radius | Full set: PRD + ARD + SPEC + PLAN + LESSONS |

**Sectioned ownership:** each loop owns specific artifacts and MUST NOT rewrite
others. `build` only flips `PLAN.md` task status cells — it MUST NOT rewrite other
artifacts. `lessons` owns `LESSONS.md` + the invariant section of `ARD.md`/`SPEC.md`.

**Plan selection:** the active plan is resolved by (in order) user naming it,
conversation context matching the slug, most-recently-modified plan folder, then
asking if still ambiguous.

**Archiving:** when all `PLAN.md` tasks are `x`, optionally move the folder to
`docs/plans/archive/`.

**Format:** artifacts are Markdown. HTML only when the user asks for it ad-hoc.

---

## §7 UBIQUITOUS LANGUAGE

Ubiquitous language is a first-class cross-cutting concern, not a side document.
Every skill participates.

- `CONTEXT.md` lives at the repo root and is shared across all plans.
- Every skill MUST read `CONTEXT.md` if it exists.
- Every name in code, spec, or plan MUST align with the glossary.
- Fuzzy or overloaded terms are sharpened; new terms are coined explicitly and
  written to `CONTEXT.md` immediately.
- `domain-modeling` (auto) maintains the glossary.

**CONTEXT.md format** — each entry has a canonical term + synonyms to avoid:

```markdown
## materialization cascade

When a lesson inside a section of a course is made real (given a spot in the file system).

_Evitar_: "lesson becomes real", "section activation", "file system placement"
```

---

## §8 COMPRESSION — caveman

`caveman` compresses spec-adjacent prose to save tokens while staying readable.

**Apply caveman to:** `PRD.md`, `ARD.md`, `SPEC.md`, `PLAN.md`, `LESSONS.md`,
`RESEARCH.md`, `CONTEXT.md` (plan artifacts).

**Do NOT apply caveman to:** code, commits, PR descriptions, diff comments,
external-facing docs, user-facing explanations, or chat-to-the-human (normal
English there).

**Symbol palette (full tables live in the `caveman` skill):**
- Grammar: drop articles/filler/auxiliaries/hedging; use short synonyms.
- Programming operators: `-> => >= <= != == && || ! in not in := ~` (ligature-clean).
- RFC 2119: `MUST`, `MUST NOT`/`NEVER`, `SHOULD`, `MAY`.
- Ranges: `1..*`, `0..1`, `n..m`; `§` for section refs.
- Type: conventional-commit words (`feat fix refactor test docs chore perf ci`).

**Emoji — CHAT ONLY, never in artifacts.** Traffic-light palette:
`🟢 PASS` `🟡 WARN` `🔴 FAIL/BLOCK/NEVER` `🔵 INFO` `🚧 WIP`, plus directional
`⬆️ ⬇️ ↗️ ↘️ ↔️` for trend. Artifacts use ASCII (`PASS FAIL WARN INFO BLOCK HARDEN WIP NEVER ✓ ✗`).
`[x]`/`[ ]` are TODO-checkbox only.

**Dropped (obscure math):** `∀ ∃ ∴ ⊥ ∈ ∉` — use words: `every exists so never in not in`.

**Preserve verbatim:** code blocks, paths, URLs, identifiers, numbers, error
strings, SQL/regex/JSON/YAML, quoted strings.

---

## §9 AGNOSTICISM (GOLDEN RULE)

Skills express **behavior** ("dispatch a reviewer", "commit a checkpoint",
"check for artifacts"). The harness adapter maps behavior to tool. A skill NEVER
names a harness, model, or tool.

**Skills MUST NOT contain:**
- References to `pi`, `Claude Code`, `Cursor`, `OpenCode`, `Antigravity`, etc.
- Tool names like `Skill`, `Task`, `subagent`, `TodoWrite`, `soul_recall`.
- Harness-specific paths like `~/.claude/skills/` or `~/.pi/agent/skills/`.
- Slash-command syntax like `/grill` in the body of a skill (use prose: "run the
  grill loop").

**What the adapter maps (Layer 4 only):** "load a skill" → native skill/read;
"dispatch a subagent" → subagent tool; "recall long-term memory" → memory substrate
(out of scope); "track a task" → todo tool or file.

**Deployability guarantee:** any skill works in any harness that can read a
`SKILL.md` and run Bash. Adding a third harness = adding a third adapter — zero
skill changes.

---

## §10 MEMORY vs ARTIFACTS

- **Agent memory** = event remembrance (what happened, what you know, how to do
  things). Lives in system prompt / memory substrate. Cross-project, tied to
  the agent.
- **Project artifacts** = deliberately written documentation (requirements,
  designs, plans, lessons). Markdown files in `docs/plans/`. Project-local,
  version-controlled.

**The critical habit:** the agent MUST remember to check and remember to update
the project artifacts. That habit is taught by `bootstrap` / the system prompt
and reinforced by memory. The artifacts themselves are NOT memory — they are the
externalized state the agent maintains.

**Write habit — when something important happens, write it to the right artifact:**
- New term coined → `CONTEXT.md`.
- Requirement clarified → `PRD.md` in the active plan.
- Invariant discovered → `ARD.md` or `SPEC.md`.
- Bug fixed → `LESSONS.md`.

**Soul Protocol is OUT OF SCOPE for this skills redesign.** It is existing
infrastructure. Skills MUST work whether Soul is present or not — degrade
gracefully to file-only.

---

## §11 RIGHT-SIZE

Ceremony scales to blast radius, never ego. A one-line fix gets a minimal
`PLAN.md`; only genuinely uncertain or high-blast-radius work runs the full
grill→design→spec→plan→build→check chain. (See §6 right-size table.)

---

## §12 CROSS-SKILL DEPENDENCIES

Skills MUST NOT import code from other skills at runtime. Skills are
independent; they operate within their own domain. When one skill's workflow
benefits from another skill's capability, the SKILL.md hints the agent to load
the companion skill. Orchestration happens at the agent conversation level, not
through code-level imports.

**Layer call rules (§3) govern cross-skill invocation:** process may call
domain+utility; domain may call domain+utility but NEVER process; utility is
leaf.

**Architectural rule:** a generic capability skill (e.g. `use-clickup`) MUST NOT
contain domain-specific constraints (workspace IDs, course terminology, academic
tags). Domain-specific constraints belong in the consuming skill. This keeps
capabilities deployable agnostically across any workspace.

---

## §13 SKILL MANAGEMENT

```
# Scaffold a new skill
python utility/skill-forge/scripts/init.py <name>

# Validate a skill against the constitution (§F/§T/§L/§A0); exit 0 = PASS
python utility/skill-forge/scripts/audit.py <name>

# Regenerate the harness-discovery manifest, grouped by layer
python utility/skill-forge/scripts/manifest.py            # write
python utility/skill-forge/scripts/manifest.py --check    # fail if stale

# Discover external skills (optional utility)
npx skills find <query>          # via skill-find
npx skills add <package>         # via skill-add, then audit with skill-forge
```

`skill-forge` is the constitution enforcer (Layer 0/3). `audit` MUST directly
validate (not just emit a prompt): frontmatter presence/shape, `user` skills have
`loop`+`deliverable`, `domain` skills warn if missing `provides`, no harness/tool
names in the body, description contains "Use when", `SKILL.md` under 500 lines.
`skill-find`/`skill-add` use `npx skills` so they work whether or not the
`skills` package is installed — `npx` resolves it at runtime.

---

## §14 COMMITS

Conventional commits: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `perf`,
`ci`. Commit after each skill passes `skill-forge audit`. Commit messages are
normal English (not caveman). Examples:

```
feat(caveman): add toned-down compression skill
fix(skill-forge): audit now rejects user skills missing deliverable
refactor(use-clickup): migrate frontmatter to layer/domain/provides
```

---

## §15 CONSTRAINTS

- **Agnosticism (core, §9):** skills MUST be deployable agnostically — no hard
  references to any agent, model, harness, or AI surface.
- **Language:** `en-US` or `es-CO`. No mixing within a single skill.
- **Size:** `SKILL.md` MUST stay under 500 lines.
- **Frontmatter (§5):** `name`, `description` with "Use when", `invocation`,
  `layer`; plus `loop`/`deliverable` (user) and `provides` (domain).
- **Structure:** `SKILL.md`, `scripts/`, `references/`. Optional: `examples/`,
  `evals/`.
- **Python:** `uv` for dependency management. `uv.lock` and `.venv/` gitignored.

---

## §16 PIPELINE

`PRD → ARD → Spec → Plan → Tasks/Tests → Review.`

`research` delegates to domain capabilities by `provides` field (e.g. generic
`research` loop delegates to `research-literature` for academic topics).
