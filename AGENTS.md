# Agent Repository Index: Orchestration & Capabilities

This file serves as a high-level index for AI agents to understand the purpose and orchestration patterns of this multi-skill repository.

## 🤖 Repository Purpose

This repository is a **Centralized Skill Hub** designed to be mounted as a workspace where an agent can discover, learn, and execute specialized capabilities. It follows the **Skill Forge** specification for token efficiency and progressive disclosure.

## 🎯 Primary Skills (Core Orchestration)

- **@[skill-forge]**: The definitive "Source of Truth" for skill development. Use this to scaffold, optimize via TDD loops, and audit skills for structural compliance.
- **@[context-engineer]**: Expert in context management, evaluation rubrics, and system design.
- **@[agent-orchestration]**: Manages multi-agent handoffs and complex task decomposition.

## 🛠️ Capability Domains

The repository contains functional skills organized into broad domains. These folders appear and disappear based on current requirements:

- **Development & Tools**: Python (uv/ruff) environments, advanced Git workflows, and build automation.
- **Data & Conversion**: MarkItDown, PDF processing, and spreadsheet (xlsx) manipulation.
- **Research & Synthesis**: Deep web research, codebase exploration, and specialized AI model tuning.
- **Office & Automation**: ClickUp management, LMS navigation (Moodle), and document generation (docx/pptx).

## 🚀 Consumption Guidelines

1. **Discovery**: Use `list_dir` on the repository root to see the current available capability folders.
2. **Alignment**: Read the frontmatter of a skill's `SKILL.md` to verify it matches your current task requirements.
3. **Execution**: Follow the instruction logic inside the skill. Prioritize using the Python scripts in `scripts/` to ensure deterministic results.
4. **Validation**: Use `/skill-audit` to verify a skill's compliance before relying on its output.

---
*Created for autonomous and semi-autonomous AI agents.*
