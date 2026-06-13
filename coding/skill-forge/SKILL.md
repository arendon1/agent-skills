---
name: skill-forge
description: >-
  The definitive framework for creating, optimizing, and auditing AI agent skills.
  Uses Test-Driven Development loops with XML prompt-based evaluation.
  Use when creating a new skill, improving an existing skill's trigger rate,
  or auditing a skill for structural/security issues.
---

# skill-forge

**`skill-forge`** generates XML prompts that agents consume to spawn subagents internally for skill evaluation. No external API calls required.

## Core Principles

1. **XML Prompt Architecture**: Scripts output structured XML prompts that agents parse to understand evaluation tasks.
2. **Agent-Native Execution**: Agents spawn subagents with different models internally to run evaluations.
3. **TDD Workflow**: Test cases are generated first, then skill is iteratively improved until tests pass.
4. **Language Consistency**: Skills must be written ENTIRELY in English (`en`) or Spanish (`es-CO`).

## 🚀 Self-Deployment

If `skill-forge`'s workflows (like `/skill-improve`, `/skill-audit`) are not appearing in your agent's slash-commands, run:
`python scripts/deploy.py --workspace .`

## Command Glossary

### `/skill-create`

Scaffold a brand new, structurally flawless skill directory.

- **Behind the scenes**: Runs `scripts/init.py`.
- **Next steps**: Focus on polishing the `description` string. Keep `SKILL.md` under 500 lines.

### `/skill-improve` (TDD Optimization)

Optimize a skill using Test-Driven Development.

- **Behind the scenes**: Runs `scripts/audit.py` which outputs an XML prompt.
- **Process**: Agent receives XML prompt with test cases and improvement criteria. Agent runs entire TDD loop internally, spawning subagents as needed.
- **Output**: Improved `SKILL.md` with description that passes all test cases.

### `/skill-audit` (Validation and Security)

Validate a skill's structure and security.

- **Behind the scenes**: Runs `scripts/audit.py` which outputs an XML prompt.
- **Process**: Agent spawns subagents internally to run different audit checks.
- **Checks**:
  - `SKILL.md` length (<500 lines)
  - Description format ("Use when..." pattern)
  - Reference folder depth (max 1 level)
  - Language consistency (en or es-CO)
  - Security scan of `scripts/` directory

## Required Skill Frontmatter

Every skill created by the forge **MUST** use this schema at the top of `SKILL.md`:

```yaml
---
name: [lowercase-with-hyphens]
description: >-
  [What it does briefly].
  Use when [Specific trigger phrases, contexts, error symptoms, file types].
---
```

## Supported Agents

skill-forge works with any agent capable of spawning subagents:

- **Antigravity CLI** - Google Antigravity agent harness
- **OpenCode** - OpenCode agent framework
- **Copilot CLI** - GitHub Copilot CLI agent
- **Kiro CLI** - Kiro custom agent framework

Agents are auto-detected by `deploy.py` based on available CLI tools.