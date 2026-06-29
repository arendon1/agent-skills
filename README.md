# agent-skills

A cohesive, self-triggering skill system for coding agents — 31 skills across
`process/` · `domain/` · `utility/` layers, with a constitution enforcer
(`skill-forge`) and a Layer 4 adapter for pi. Merges mechanisms from Cavekit,
Superpowers, and Matt Pocock into one harness-agnostic architecture.

- **Constitution:** `AGENTS.md` — frontmatter schema, layers, triggering,
  per-plan artifacts, ubiquitous language, caveman compression, agnosticism.
- **Design source of truth:** `architecture-plan.html`, `HANDOFF.md`.
- **Constitution enforcer:** `utility/skill-forge` — `audit.py` is the
  direct, exit-code enforcer of the constitution.

## Install — two paths, two capability tiers

This repo is designed to be installed by Vercel's skills manager (`npx skills`)
or directly into pi (`pi install`). Both are verified; pick by what you need.

### Tier 1 — Full self-triggering (pi)

```bash
pi install <this-repo>           # project-local
pi install -g <this-repo>        # or global (~/.pi/)
```

One command. `pi install` reads our `package.json` (`pi.extensions` +
`pi.skills`) and gives you:

- ✅ All 31 skills discoverable (pi scans the layer buckets via
  `resources_discover`).
- ✅ **Bootstrap auto-triggering** — the `bootstrap` skill body is injected
  at session start and after every compaction (the §4 self-triggering
  behavior — check for skills + `CONTEXT.md` + the active plan before
  responding).

This is the recommended path for pi users. The adapter is the **only**
harness-coupled code in the repo, by design (§9 agnosticism).

### Tier 2 — Cross-harness discovery (every harness)

```bash
npx skills add <this-repo>      # uses 'npx skills' (the Vercel skills manager)
```

This is the path for OpenCode, Claude Code, Cursor, Windsurf, Cline, and every
other harness the skills manager supports. `SKILL.md` files get copied (or
symlinked, depending on flags) into each harness's conventional skill dir.

- ✅ All 31 skills discoverable + manually invokable on every harness.
- ❌ **No bootstrap injection** — `skills add` ships `SKILL.md` files only,
  never runtime hooks/exensions, so auto-triggering is not available. Skills
  work when you ask for them ("Use when…" triggers fire normally).

### Which one do I want?

| You want… | Use |
|---|---|
| Full self-triggering on pi (recommended) | `pi install` |
| Self-triggering on another harness | that harness' adapter (Tier 1 equivalent); build it in `adapters/<harness>/` |
| Skills on every harness, manual invocation is fine | `npx skills add` |

The buckets (`process/`/`domain/`/`utility/`) are a **source-repo** concern —
human browsing + the `skills` CLI's grouping display. Deployed locations are
flat (`<harness>/skills/<skill>/`) by design.

## What this is

A skill system, not a framework for apps. The deliverables are:

- 31 `SKILL.md` files (each = one skill, each self-contained).
- A constitution (`AGENTS.md`) that every skill is validated against.
- An enforcer (`utility/skill-forge`) that audits and scaffolds.
- Per-harness adapters (Layer 4) — pi today; OpenCode/Claude/etc. as needed.

Skills express **behavior**; adapters map behavior to harness tools. Skills
never name a harness, model, or tool.

## Working in this repo

All script invocations are from the repo root:

```bash
# audit a skill (exit 0 = PASS, 1 = FAIL)
python utility/skill-forge/scripts/audit.py <skill-name>

# regenerate the marketplace manifest (Format A: groups skills by layer)
python utility/skill-forge/scripts/manifest.py
python utility/skill-forge/scripts/manifest.py --check   # fail if stale

# scaffold a new skill
python utility/skill-forge/scripts/init.py <name> \
    --invocation user --layer process \
    --loop <name> --deliverable "<thing>"

# check the constitution
cat AGENTS.md
```

## Layout

```
.
├── AGENTS.md                      ← constitution
├── architecture-plan.html         ← design source of truth (read-only)
├── package.json                   ← pi package manifest (extensions + skills)
├── .claude-plugin/
│   └── marketplace.json           ← generated; Format A; groups by layer
├── .pi/extensions/
│   └── agent-skills.ts            ← Layer 4 adapter (pi)
├── process/                       ← 20 skills
├── domain/                        ←  6 skills
└── utility/                       ←  5 skills (includes skill-forge, bootstrap, caveman)
```
