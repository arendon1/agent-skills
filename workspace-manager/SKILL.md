---
name: workspace-manager
version: 3.0.0
type: methodology
description: >-
  Automates workspace setup and organization. Deploys agent-centric structures,
  optimizes .gitignore, and handles project cleanup across various agent types
  with zero friction.
keywords: [workspace, init, cleanup, architecture, agents, organization]
---

# Workspace Manager Skill

This skill transforms any directory into a high-performance, agent-ready workspace. It focuses on reducing friction when moving between different AI agents (Claude, Gemini, etc.) and maintaining a clean "shipping state" repository.

## 🚀 Self-Deployment & Bootstrapping

If this skill's workspace workflows (like `/workspace-init`, `/workspace-cleanup`) are not appearing in your agent's slash-commands, run the following command from the skill's root directory:
`python scripts/bootstrap.py --workspace .`

This will automatically detect your agent's configuration directory (e.g., `.agents`, `.cursor`, `.gemini`, or `.agent`) and deploy the necessary `.md` or `.mdc` files.

## 🧭 Core Functionality

1. **Workspace Initialization**: Sets up a standardized directory structure that supports multiple agent workflows, IDE configurations, and essential project files.
2. **Automated Cleanup**: Optimized `.gitignore` management and automated auditing of "orphan" files at the root level, moving them to a `.review` folder for later inspection.
3. **Multi-Agent Support**: Deploys a robust `.agent/` hierarchy to consolidate context, rules, and skills for any LLM agent.

## Quick Reference Commands

| Task | Action | Command |
| :--- | :--- | :--- |
| **Initialize Workspace** | `/workspace-init` | Deploys basic structure and agent folders |
| **Cleanup Workspace** | `/workspace-cleanup` | Organizes root, updates ignore patterns |
| **Interpret Workspace** | `python scripts/interpret_structure.py [path]` | Analyzes existing hierarchy |
| **Validate Compliance** | `python scripts/enforce_structure.py [path]` | Checks for organization issues |

## 🏗️ Deployed Structure (`/workspace-init`)

The initialization command creates the following hierarchy:

- `.agent/`
  - `workflows/`: YAML/MD files defining automated tasks.
  - `skills/`: Local skill definitions.
  - `rules/`: Global and project-specific agent rules.
  - `specs/`: Technical specifications and design docs.
  - `steering/`: Prompt fragments to guide agent behavior.
  - `hooks/`: Scripts triggered by workspace events.
- `.vscode/settings.json`: Recommended IDE settings for a clean experience.
- `PROJECT.md`: The absolute source of truth for the codebase structure.
- `README.md` & `docs/`: Standard documentation entry points.
- `.gitignore`: Pre-populated with efficient, project-aware patterns.

## 🧹 Cleanup Logic (`/workspace-cleanup`)

- **Ignore Optimization**: Appends missing common patterns for OS, IDEs, and language-specific temp files.
- **Orphan Review**: Moves files that don't belong in the root to `.review/`.
- **Audit Traceability**: Generates `.review/REVIEW.md` listing every moved item with a timestamp for manual audit.

## 🧭 Discovery & Persistence

1. **PROJECT.md Authority**: Always use `PROJECT.md` or `CLAUDE.md` as the map for valid file placement.
2. **Non-Destructive Cleanup**: Cleanup moves files rather than deleting them, ensuring no loss of work during organization.
3. **No Forced Reorganization**: Respects detected patterns (`kebab-case`, `snake_case`) while enforcing consistency.
