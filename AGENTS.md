# AGENTS.md

Repository of **agent skills** built with [skill-forge](skill-forge/SKILL.md). Each subdirectory is an independent, deployable skill.

## Constraints

- Skills must be entirely in `en-US` or `es-CO`. No mixing.

## ClickUp Sync Rule

After any `gestionar-cursos init` or `gestionar-cursos estado` completes, **always ask the user** before running ClickUp sync:

> "Curso(s) inicializados localmente. ¿Sincronizar con ClickUp?"
>
> Opciones: `Sincronizar` / `Dry-run primero` / `No`

If confirmed, run `cli_clickup.py` with the period directory.
