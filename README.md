# agent-skills

Personal collection of AI agent skills. Each subdirectory is an independent,
deployable skill built with [skill-forge](skill-forge/SKILL.md).

Skills are self-contained directories at the repo root. Each contains a
`SKILL.md` and supporting files. Discovered dynamically — the directory listing
is the source of truth.

## Quick start

```bash
# Scaffold a new skill
python skill-forge/scripts/init.py my-skill --path .

# Validate its structure
python skill-forge/scripts/audit.py my-skill
```

## Principles

- **Agnostic by default.** Skills never reference a specific agent, model, harness, or
  AI surface. Deployable anywhere.

## Conventions

- Skills are written in `en-US` or `es-CO` (never mixed within one skill)
- `SKILL.md` stays under 500 lines
- Conventional commits (`feat`, `fix`, `refactor`, `chore`)
- Python toolchain uses `uv`

## License

MIT — see [LICENSE](LICENSE). The repo license covers the collection, organization,
and original skills. Skills imported from third-party sources retain their upstream
licenses.
