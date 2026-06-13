# AGENTS.md

> Runtime conventions for pi in the `agent-skills` project.

## §G GOAL

Collection of agent skills — each subdirectory is an independent, deployable skill.
pi builds, audits, and maintains skills here using skill-forge.

## §D DISCOVERY

Skills come and go. pi MUST discover skills dynamically by scanning subdirectories
for `SKILL.md` files. NEVER hardcode a skill list — the active set is whatever
directories exist right now. The harness lockfile (if present) is for the harness,
not for pi.

Skills are organized into **category directories** at the repo root. Categories
are a discovery aid — agents scan recursively and the directory path encodes
grouping without harness-specific metadata. No category directory shall contain a
`SKILL.md` itself; they are containers, not skills.

## §C CONSTRAINTS

- **Agnosticism (core):** Skills MUST be deployable agnostically — no hard references to
  any specific agent, model, harness, or AI surface (pi, OpenCode, VS Code, Antigravity,
  Claude Code, etc.). A skill works the same regardless of where it runs.
- **Language:** Skills in `en-US` or `es-CO`. No mixing within a single skill.
- **Size:** `SKILL.md` must stay under 500 lines.
- **Frontmatter:** `name:` (lowercase-hyphens), `description:` with "Use when..." pattern.
- **Structure:** `SKILL.md`, `scripts/`, `references/`. Optional: `examples/`, `evals/`.
- **Categories:** `kebab-case` directory names at repo root. Single-word preferred;
  multi-word uses hyphens (e.g., `academic-writing`). Categories are discovery
  groupings, not deployment rules — they are purely organizational.
- **Commits:** Conventional commits — `feat`, `fix`, `refactor`, `chore`.
- **Python:** `uv` for dependency management. `uv.lock` and `.venv/` are gitignored.

## §X CROSS-SKILL DEPENDENCIES

Skills MUST NOT import code from other skills at runtime. Skills are independent;
they operate within their own domain. When one skill's workflow benefits from
another skill's capability, the SKILL.md should hint the agent to load the
companion skill. Orchestration happens at the agent conversation level, not
through code-level imports.

**`gestionar-cursos` → `use-clickup`**: `gestionar-cursos` SKILL.md instructs the
agent to load `use-clickup` for ClickUp API operations. The `sys.path` import in
`cli_clickup.py` will be removed as part of the category restructuring.

**Architectural rule:** `use-clickup` is a generic ClickUp API wrapper — it MUST
NOT contain domain-specific constraints (workspace IDs, course terminology,
academic tags). Any workspace or space-level constraints belong in the consuming
skill (`gestionar-cursos`). This keeps `use-clickup` deployable agnostically
across any ClickUp workspace.

## §S SKILL-FORGE

```
# Scaffold a new skill
python skill-forge/scripts/init.py <name> --path .

# Validate a skill's structure
python skill-forge/scripts/audit.py <skill-dir>
```
