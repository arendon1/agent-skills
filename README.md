# agent-skills

A collection of **35 skills** for coding agents — process loops, domain
capabilities, and utility tools — organized into three layers and shipped as a
single installable package. Skills express **behavior**; an optional thin
adapter maps behavior to your harness's tools.

> **Constitution:** every skill is validated against [`AGENTS.md`](./AGENTS.md)
> by `utility/skill-forge` (the enforcer). The constitution is the source of
> truth for frontmatter, layer rules, and triggering contracts.

---

## Install

Use Vercel's [`skills`](https://www.npmjs.com/package/skills) CLI. It copies
(or symlinks) every `SKILL.md` into your harness's conventional skill
directory, so a one-liner works on every supported agent:

```bash
npx skills add <this-repo>
# or, to a specific global location
npx skills add <this-repo> -g
```

That's it. Once installed, every skill becomes available to your agent — most
auto-trigger on context (the `"Use when …"` line in each frontmatter); the few
that are user-invoked loops (e.g. `grill`, `plan`, `build`) get typed by name
when you want their named deliverable.

### What you get

- ✅ All 35 skills discoverable by your harness.
- ✅ All 35 skills audited against the constitution (`AGENTS.md`) before ship.
- ✅ Compatible with every harness the `skills` CLI supports (Claude Code,
  Cursor, Windsurf, Cline, OpenCode, …).
- ❌ No auto-injection at session start — `skills add` ships `SKILL.md` files
  only, never runtime hooks. If you want the `bootstrap` skill auto-injected
  at session start, see the [Adapters](#adapters-optional) section.

### Pin a version

```bash
npx skills add <this-repo>@v1.2.0
```

---

## Repository structure

The repo is the **source**. The `skills` CLI flattens it into
`<your-harness>/skills/<skill-name>/` on install, but the source layout is
deliberately grouped into three layer-buckets so humans can browse and
contribute.

```
.
├── AGENTS.md                      ← constitution (frontmatter schema, layer rules, triggering)
├── package.json                   ← manifest (also used by some harnesses)
├── .claude-plugin/
│   └── marketplace.json           ← generated, Format A: groups by layer
├── process/                       ← 20 skills — loops + disciplines
├── domain/                        ←  8 skills — domain-specific capabilities
└── utility/                       ←  6 skills — cross-cutting tools
```

### The three layers

Skills are organized into strict layers with a one-way call rule. The rule is
enforced by `skill-forge audit`, not by social agreement.

| Layer | Bucket    | Count | Role | Examples |
|------:|-----------|------:|------|----------|
| 1     | `process` | 20    | Loops that produce a deliverable (`grill`, `plan`, `build`, `review` …) and reusable disciplines (`tdd`, `debug`, `verify`, `lessons`, `git`, `dispatch` …) | `grill`, `plan`, `tdd`, `debug`, `verify` |
| 2     | `domain`  | 8     | Domain-specific capabilities that operate inside a process loop | `use-clickup`, `research-literature`, `gestionar-cursos`, `generar-paper` |
| 3     | `utility` | 5     | Cross-cutting leaf tools; one of them (`bootstrap`) is session-enabling | `skill-forge`, `bootstrap`, `caveman`, `skill-find`, `skill-add` |

**Call rule (one-way):** process → domain → utility. A `domain` skill MUST
NOT call a `process` skill. A `utility` skill MUST NOT call anything. The
reason: if a domain loop could trigger a process loop, control inverts and
the agent stops being a peer — it becomes a dispatcher with amnesia.

### Anatomy of a skill

Each skill is one directory with at minimum a `SKILL.md`. Most also have
`scripts/`, `references/`, and optional `examples/`, `evals/`, `assets/`.

```
process/grill/
├── SKILL.md        ← required; the contract
├── references/     ← cited sources, glossaries, deep dives
├── examples/       ← worked inputs/outputs (optional)
└── evals/          ← tests + acceptance criteria (optional)
```

The `SKILL.md` is **the contract**. It has two parts:

1. **YAML frontmatter** — declares name, description (must contain `Use when`),
   `invocation` (`auto` / `user` / `bootstrap`), `layer`, and for `user`-invoked
   skills a `loop` + `deliverable`.

   ```yaml
   ---
   name: grill
   description: |
     Sharpen a fuzzy idea into requirements before spec. Calibrates scope,
     surfaces unknowns, and co-designs the mission.
     Use when a task is vague, a PRD is missing, or scope is unclear.
   invocation: user
   layer: process
   loop: grill
   deliverable: PRD.md
   ---
   ```

2. **Markdown body** — the procedure: when to fire, numbered steps, pitfalls,
   and verification. Skills stay under 500 lines so a single context window
   can hold one skill plus the active task.

### Triggering model

Every skill declares one of three `invocation` values:

| Value       | Count | Contract |
|-------------|------:|----------|
| `auto`      | ~30   | Self-triggers on context, symptoms, or behavior. Default for disciplines + domain capabilities. |
| `user`      | ~3    | Human invokes a named loop producing a specific deliverable. MUST declare `loop` + `deliverable`. |
| `bootstrap` | 1     | Injected at session start and after compaction. Only `utility/bootstrap` holds this role. |

This is what eliminates ambiguous entry points like `grill-me` vs
`brainstorming`: a `user` skill MUST ship a `deliverable`, so the loop has a
named output you can ask for.

---

## Adapters (optional)

The repo is **harness-agnostic at the core** — skills name behaviors, never
tools. The optional adapter layer is the only place where a skill's behavior
gets bound to a specific harness's tools (e.g. auto-injecting `bootstrap` at
session start, or mapping agnostic behaviors to concrete tool names).

| Harness | Adapter path | Mechanism |
|---------|-------------|-----------|
| **pi** | `.pi/extensions/agent-skills.ts` | TS extension hooking `resources_discover`, `session_start`, `session_compact`, `context` |
| **Hermes** | `adapters/hermes/` | Python plugin (`plugin.yaml` + `__init__.py`) hooking `on_session_start` + `pre_llm_call` |

You do **not** need an adapter to use the skills — `npx skills add` is the
recommended path for everyone. Adapters add the full self-triggering experience:
auto-injecting `bootstrap` at session start and after compaction, plus the
behavior→tool mapping. If you want that on a specific harness, install the
matching adapter.

### Hermes

```bash
# From the repo root — symlink into Hermes's plugins directory
ln -sf "$(pwd)/adapters/hermes" ~/.hermes/plugins/agent-skills
hermes plugins enable agent-skills
# Takes effect on the next session (/reset or restart).
```

The Hermes adapter uses the `pre_llm_call` hook to inject the bootstrap skill
body + a Hermes-specific tool mapping into the first turn of every new session.
Because `pre_llm_call` injection is ephemeral (not persisted to conversation
history), it naturally re-injects after context compaction — no separate
`session_compact` hook needed.

---

## Working in this repo (contributors)

All script invocations are from the repo root.

```bash
# audit a skill against AGENTS.md (exit 0 = PASS, 1 = FAIL)
python utility/skill-forge/scripts/audit.py <skill-name>

# regenerate the marketplace manifest (Format A: groups by layer)
python utility/skill-forge/scripts/manifest.py
python utility/skill-forge/scripts/manifest.py --check   # fail if stale

# scaffold a new skill
python utility/skill-forge/scripts/init.py <name> \
    --invocation user --layer process \
    --loop <name> --deliverable "<thing>"

# read the constitution
cat AGENTS.md
```

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the full contributor guide and
[`AGENTS.md`](./AGENTS.md) for the rules every skill must follow.

---

## License

MIT.
