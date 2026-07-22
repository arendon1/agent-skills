# Contributing a skill

> A guide for adding a new skill to this repo. **All rules live in `AGENTS.md`
> and are enforced by `skill-forge`.** This document does not invent policy —
> it sequences the work and points at the authoritative source for each rule.
> If something here disagrees with `AGENTS.md` or `skill-forge`, the latter
> wins.

## Before you start

Read these (they're short):

- **`AGENTS.md`** — the constitution. At minimum skim §F (frontmatter schema),
  §L (layers + call rules), §T (triggering — `auto` / `user` / `bootstrap`),
  §A0 (agnosticism — what skills must never contain).
- **`utility/skill-forge/SKILL.md`** — the enforcer. The `WHAT AUDIT ENFORCES`
  table is the authoritative checklist. The `COMMANDS` section has the exact
  commands. Audit will run against your skill and refuse anything in that
  table; matching it during authoring is faster than fixing afterwards.

You do **not** need to read every skill to learn conventions. `skill-forge` +
`AGENTS.md` are sufficient. Existing skills are illustrative, not normative.

---

## Step 1 — Decide the layer

The `layer:` field (and the directory you put the skill in) must be one of
`process` / `domain` / `utility`. The criteria below are **inferred from the 33
existing skills and the call rules in AGENTS.md §3** — the constitution itself
does not define an assignment algorithm, so use your judgment, and if in doubt
look at which bucket analogous skills sit in.

| Layer | When to use | Call rule (§3) | Frontmatter |
|---|---|---|---|
| **process** | A step in the development methodology (`grill`, `plan`, `build`, `review`) or a discipline the loop skills invoke (`tdd`, `verify`, `debug`, `lessons`). The SDD pipeline + its quality gates. | May call L1 disciplines, L2 domain, L3 utility. | `invocation` defaults to `auto`; `user` only when it's a named loop with a deliverable (`grill`, `plan`, `review`, ...). |
| **domain** | Integrates a specific external service or field. Generic capability skills (`use-clickup`, `research-literature`, `make-a-diagram`) live here too, plus domain-specific loops that use them (`gestionar-cursos`, `generar-paper`, `analyze-model`). | May call L2 domain + L3 utility. MUST NOT call L1 process (never inverts control). | `layer: domain` requires `provides: [capabilities]` (audit warns if missing). |
| **utility** | Cross-cutting support the other skills consume, plus the always-on `bootstrap` and the skill management suite (`caveman`, `skill-forge`, `skill-find`, `skill-add`). | Nothing — leaf skills. | `invocation: auto` (except `bootstrap`, which is `bootstrap`-invoked). |

The bucket directory name MUST match the layer: `process/<name>/`,
`domain/<name>/`, or `utility/<name>/`. The frontmatter `layer:` field must
match the bucket (`audit` enforces this indirectly via `name` == dir name;
keep them aligned by construction).

## Step 2 — Scaffold the skill

```bash
# From the repo root.
python utility/skill-forge/scripts/init.py <name> \
    --invocation auto|user \
    --layer process|domain|utility \
    [--loop <name>] [--deliverable "<thing>"] \
    [--provides <capability> ...]
```

`init.py` creates `<bucket>/<name>/SKILL.md` with frontmatter stubs and the
`scripts/`, `references/`, `examples/`, `evals/` directories. It does NOT
write the body. See `init.py --help` for flags.

**If you skip `init.py` and write a SKILL.md by hand**, mirror the frontmatter
it produces (see Step 3) and place the skill in the correct bucket. `audit`
will still validate it.

## Step 3 — Fill the frontmatter (AGENTS.md §5 + §4)

`audit` enforces this table verbatim. Match it during authoring so you don't
get a FAIL later.

| Field | Required? | Notes |
|---|---|---|
| `name` | yes | lowercase-hyphens; MUST equal the directory name. |
| `description` | yes | First line: what the skill does. **Must contain the literal `Use when`** (or `Usa cuando` for `es-CO` skills). The `Use when ...` part is what makes the skill auto-triggerable. |
| `invocation` | yes | `auto` (default — self-triggers from context), `user` (human invokes a named loop with a deliverable), or `bootstrap` (reserved — only the `bootstrap` skill may use this). |
| `layer` | yes | `process` / `domain` / `utility` — must match the bucket directory. |
| `loop` | when `invocation: user` | Short loop name (used in prose: "run the grill loop"). |
| `deliverable` | when `invocation: user` | Named output the loop produces (e.g. `"PRD.md + plan folder"`). |
| `provides` | when `layer: domain` | One or more capabilities, e.g. `[clickup-api]`. Other capabilities consume these. |
| `language` | optional | `en-US` or `es-CO`. No mixing within a skill. |
| `metadata` | optional | `{ version: "X.Y.Z", ... }`. |

## Step 4 — Write the body

Two hard rules the body must satisfy (`audit` enforces both):

1. **Agnosticism (AGENTS.md §9).** No references to specific harnesses
   (`pi`, `Claude Code`, `OpenCode`, `Cursor`, `Antigravity`, `Copilot`,
   `Kiro`), no tool-API names (`TodoWrite`, `soul_recall`), no slash-command
   syntax (`/grill` in prose — use `"run the grill loop"`). The adapter
   (Layer 4) maps behavior to tools; skills describe behavior.
2. **Size (AGENTS.md §15).** `SKILL.md` must be under 500 lines. Right-size
   the skill (AGENTS.md §11) — a small skill in one folder beats a sprawling
   one.

Two soft rules worth following:

- **caveman compression (AGENTS.md §8)** for plan artifacts
  (`PRD/ARD/SPEC/PLAN/LESSONS/RESEARCH/CONTEXT.md`). The full palette +
  `chat-only` emoji rules live in the `caveman` skill. Code, commits, and
  user-facing prose stay in normal English.
- **Ubiquitous language (AGENTS.md §7).** Use canonical terms from
  `CONTEXT.md`. Coining a new term? Add it to `CONTEXT.md` (or invoke the
  `domain-modeling` discipline).

### Anatomy of a passing `SKILL.md`

```markdown
---
name: <skill-name>
description: |
  <one-line summary of what it does>.
  Use when <specific triggers — symptoms, contexts, phrasings>.
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# <skill-name>

## WHEN (self-trigger)

- <trigger 1>
- <trigger 2>

## OWNERSHIP

What this skill owns vs hands off. One short paragraph.

## STEP 0 — READ EXISTING STATE

What the skill reads first (active plan, CONTEXT.md, prior artifact).

## STEP N — <the work>

Numbered, testable steps. Each cites the invariants/interfaces it touches.

## WHEN TO STOP

Done conditions — bullet list.

## BOUNDARIES

MUST / MUST NOT list. Short, behavioral, not legalistic.
```

The smallest passing skill in the repo is `skill-find` (~78 lines). Use it as
a shape reference when in doubt.

## Step 5 — Audit + regenerate manifest

```bash
# Must exit 0.
python utility/skill-forge/scripts/audit.py <skill-name>

# Regenerate the marketplace manifest (now lists the new skill in its layer).
python utility/skill-forge/scripts/manifest.py

# Fail if the manifest is stale (catches forgotten regenerations).
python utility/skill-forge/scripts/manifest.py --check
```

If `audit` fails, fix the skill (do NOT weaken the audit). The common
fails and fixes:

- Missing `Use when` in `description` → add it (the trigger phrase is what
  makes the skill auto-discoverable).
- `user` skill without `loop`/`deliverable` → add them.
- `domain` without `provides` → add `[<capability>]`.
- Harness name in body → rephrase as behavior (e.g. instead of "open in pi",
  write "let the harness open it"). The `pi` you write inside a backtick
  doesn't match (word boundary), but `pi as the math constant`, `api/pip` etc.
  don't match either — only the standalone word.
- `SKILL.md` over 500 lines → right-size (split into sub-helpers, link
  `references/`).

## Step 6 — Verify end-to-end

After `audit` passes and the manifest is fresh, confirm the harness can find
your skill. The recommended path is the Vercel `skills` CLI — it works on
every supported harness:

```bash
# Cross-harness discovery + grouping by layer.
npx skills add . --list -y | grep <skill-name>
```

If you are using a harness with a dedicated adapter (e.g. pi) and want the
full self-triggering experience:

```bash
pi install . -l -a
# In a fresh pi prompt:
#   "How many skills are available to you? Reply with just a number."
# Expect 34 (one more than before).
```

Either path is fine — pick the one your harness supports. The skill is
correct as long as `audit` passes and your harness lists it.

## Step 7 — Commit

One commit per skill. Conventional commit, normal English (NOT caveman):

```
feat(<skill>): <one-line goal>
refactor(<skill>): <what changed, no behavior change>
fix(<skill>): <bug fixed, link §V if an invariant moved>
docs(<skill>): <SKILL.md / references update only>
```

---

## Quick reference — what each doc owns

| Question | Answer lives in |
|---|---|
| What fields go in frontmatter? What are the enforcer checks? | `AGENTS.md` §5 + `utility/skill-forge/SKILL.md` (WHAT AUDIT ENFORCES) |
| Which layer should this skill be? | This doc (Step 1) + AGENTS.md §3 (call rules + existing catalog) |
| How do I invoke the scaffolder / auditor / manifest generator? | `utility/skill-forge/SKILL.md` (COMMANDS section) |
| What does the body look like? | This doc (Step 4 anatomy) + AGENTS.md §9 (agnosticism) + §8 (caveman boundaries) |
| Where does the skill live in the repo? How is it deployed? | `README.md` (install paths) + AGENTS.md §2 (bucket layout) |

---

## Install path for users (not contributors)

If you're here to **use** the skills, not write one, skip everything above and
run:

```bash
npx skills add <this-repo>
```

That's the install path documented in `README.md`. This doc is for adding
skills to the repo. See `AGENTS.md` for the rules, `skill-forge` for the
enforcer, and `README.md` for the user-facing install.
