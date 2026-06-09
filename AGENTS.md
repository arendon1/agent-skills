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

## §C CONSTRAINTS

- **Language:** Skills in `en-US` or `es-CO`. No mixing within a single skill.
- **Size:** `SKILL.md` must stay under 500 lines.
- **Frontmatter:** `name:` (lowercase-hyphens), `description:` with "Use when..." pattern.
- **Structure:** `SKILL.md`, `scripts/`, `references/`. Optional: `examples/`, `evals/`.
- **Commits:** Conventional commits — `feat`, `fix`, `refactor`, `chore`.
- **Python:** `uv` for dependency management. `uv.lock` and `.venv/` are gitignored.

## §X CROSS-SKILL DEPENDENCIES

`gestionar-cursos/scripts/cli_clickup.py` imports from `use-clickup/scripts/` at runtime.
Changes to `use-clickup` module/function names break `gestionar-cursos`. Check both when
renaming.

## §S SKILL-FORGE

```
# Scaffold a new skill
python skill-forge/scripts/init.py <name> --path .

# Validate a skill's structure
python skill-forge/scripts/audit.py <skill-dir>
```
