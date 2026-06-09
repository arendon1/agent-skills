# agent-skills

Personal collection of AI agent skills. Each subdirectory is an independent,
deployable skill built with [skill-forge](skill-forge/SKILL.md).

## Structure

```
agent-skills/
├── skill-forge/         # Skill scaffolding and auditing toolkit
├── use-clickup/         # ClickUp API integration
├── gestionar-cursos/    # Course management (depends on use-clickup)
├── analyze-llm-model/   # LLM cost/quality analysis
├── escritura-academica/ # Academic writing assistant
├── git-master/          # Proactive version control for AI agents
├── make-a-diagram/      # Mermaid diagram generation
└── README.md
```

Skills are discovered dynamically — the directory listing is the source of truth.
New skills can be added as directories at any time.

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
