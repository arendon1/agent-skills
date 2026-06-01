# AGENTS.md

Collection of **agent skills** built with [skill-forge](skill-forge/SKILL.md). Each subdirectory is an independent, deployable skill.

## Constraints

- Skills must be entirely in `en-US` or `es-CO`. No mixing.
- SKILL.md stays under 500 lines.
- Frontmatter uses `name:` (lowercase-hyphens), `description:` with "Use when..." pattern.
- Skill directory structure: `SKILL.md`, `scripts/`, `references/`. Optionally `examples/`, `evals/`.

## Creating skills

Scaffold with skill-forge:
```
python skill-forge/scripts/init.py <name> --path .
```

Validate structure:
```
python skill-forge/scripts/audit.py <skill-dir>
```

## Cross-skill dependencies

`gestionar-cursos/scripts/cli_clickup.py` imports from `use-clickup/scripts/` at runtime via `sys.path`. Changes to `use-clickup` module/function names break `gestionar-cursos`. Check both when renaming.

## Commits

Conventional commits: `feat`, `fix`, `refactor`, `chore`.

## Python toolchain

Skills use `uv` for dependency management. `uv.lock` and `.venv/` are gitignored at the root level. Some skills have their own `.gitignore`.
