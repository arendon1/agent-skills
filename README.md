# LLM Agent Skills Repository

This repository is a **Dynamic Orchestration Hub** for LLM-based agents. It is designed to host a modular, evolving collection of "Superpowers"—structured knowledge bases and deterministic toolsets that enable agents to perform complex, domain-specific tasks with high reliability and low token overhead.

## 🧠 Core Philosophy: The Skill-Forge Logic

The repository operates on the principle that AI agents are most effective when they follow a **Discovery-to-Execution** lifecycle, rather than having all context loaded at once.

### 1. Token-Efficient Hierarchy

To prevent context rot, the repository uses a tiered loading system:

- **Global Indexing:** Agents first discover skills by listing directories or reading high-level summaries (`AGENTS.md`). Only the `name` and `description` are exposed initially.
- **Progressive Disclosure:** Full instructions (`SKILL.md`) are only loaded once an agent determines a high alignment (e.g., >1% relevance) with the current task.
- **Deep Context:** Massive documentation or specific schemas reside in `references/` or `resources/`, loaded only when the agent needs specific technical details.

### 2. Deterministic Tooling vs. Probabilistic Reasoning

Whenever possible, heavy logic is offloaded to Python scripts within each skill's `scripts/` directory. This ensures:

- **Reliability:** The LLM manages the workflow; the code handles the execution.
- **Consistency:** Complex operations (like file conversions or API syncs) follow a repeatable path regardless of the model's "mood."

### 3. The "Skill Forge" Standard

New capabilities are added following the **Skill Forge** doctrine:

- **Audit-First:** Every skill must pass structural and security audits before deployment.
- **TDD Optimization:** Descriptions and instructions are iteratively refined using trigger-evaluation scripts to ensure agents know exactly *when* to invoke the skill.

## 🛠️ Repository Mechanics

### For Agents

1. **Explore:** Use `list_dir` to see available folders. Folders are named after the capability.
2. **Evaluate:** Read only the YAML frontmatter of a candidate skill to verify its trigger conditions.
3. **Execute:** Follow the `SKILL.md` instructions, prioritizing the use of provided CLI tools or scripts.

### For Developers

- **Modularity:** Skills are self-contained. Deleting a directory removes the capability without breaking the repo's core orchestration.
- **Slash Workflows:** Use project-level commands (`/skill-create`, `/skill-audit`) to scaffold and validate skills. These scripts handle the heavy lifting of repository maintenance.

---
*Empowering AI agents through structured, deterministic capabilities.*
