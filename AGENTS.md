# Agent Repository Index: Orchestration & Capabilities

This file serves as a high-level index for AI agents to understand the purpose and orchestration patterns of this multi-skill repository.

## 🤖 Repository Purpose

This repository is a **Centralized Skill Hub** designed to be mounted as a workspace where an agent can discover, learn, and execute specialized capabilities. It follows the **Skill Mastery** specification for token efficiency and progressive disclosure.

## 🎯 Primary Skills (Core Orchestration)

- **@[skill-mastery]**: The "Source of Truth" for skill development. Use this to validate or build other skills.
- **@[context-engineer]**: Expert in context management, evaluation rubrics, and system design.
- **@[agent-orchestration]**: Manages multi-agent handoffs and complex task decomposition.

## 🛠️ Functional Skill Categories

### Development & Tools

- **@[python-uv]**: Fast Python package and project management.
- **@[git-master]**: Advanced git workflows and commit generation.
- **@[markitdown]**: Converts various file formats to Markdown.
- **@[scientific-schematics]**: Generates diagrams and schematics (Mermaid, SVG).
- **@[stitch-ui-generator]**: (New) AI-powered UI generation via Google Stitch API (HTML/jQuery focus).

### Research & Information

- **@[deep-research]**: Comprehensive web and codebase exploration.
- **@[notebooklm-skill]**: Integration with NotebookLM for deep content synthesis.
- **@[google-ai-mode-skill]**: Specialized patterns for Google AI models.

### Office & Automation

- **@[office]**: Handling Word, Excel, and PowerPoint automation.
- **@[clickup-manager]**: Project management and task tracking via ClickUp.
- **@[monday-course-manager]**: Course and task management via Monday.com.
- **@[moodle-navigator]**: Navigation and interaction with Moodle LMS.

### Specialized

- **@[academic-author]**: Scholarly writing and bibliography management (Typst, BibLaTeX).

## 🚀 Consumption Guidelines

1. **Selection**: Read the `description` in the directory's frontmatter to decide if a skill is relevant.
2. **Loading**: Trigger the skill by reading its root `SKILL.md`.
3. **Execution**: Prefer using scripts in `scripts/` over raw LLM reasoning for repetitive or complex logic to minimize token costs and ensure reliability.
4. **Validation**: Use `/audit` to verify skill compliance.

---
*Created for autonomous and semi-autonomous AI agents.*
