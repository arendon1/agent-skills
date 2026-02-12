# LLM Agent Skills Repository

This repository is a dynamic, evolving collection of skills for LLM-based agents (e.g., Claude, Gemini). These skills provide structured knowledge, workflows, and tools designed to enhance agent capabilities across various domains.

## 📂 Repository Structure

The skills are organized as independent modules at the root of the repository. Each skill follows a standardized format to ensure consistency and efficiency:

- **Modular Design:** Skills are categorized by function (e.g., version control, orchestration, file conversion).
- **Direct Access:** Each subdirectory contains a `SKILL.md` file that serves as the entry point and primary instruction set for that specific capability.
- **Dynamic Collection:** This repository integrates and removes skills based on evolving requirements and best practices. Explore the directories to see the current available toolset.

## 🚀 Getting Started

To use these skills with your AI agent:

1. **Locate the Skill:** Navigate to the folder of the skill you wish to use.
2. **Read the Instructions:** Open the `SKILL.md` file (and any reference files in `references/`) to understand the skill's capabilities and commands.
3. **Load the Skill:** Provide the content of the skill files to your agent's context or configuration system.

## 🛠️ Creating New Skills

We follow the **Skill Mastery** standard for all new additions. Please refer to [`skill-mastery/SKILL.md`](skill-mastery/SKILL.md) for detailed instructions on:

- **Structure:** Keeping `SKILL.md` concise (<500 lines) and using `references/` for detailed content.
- **Format:** Using strict YAML frontmatter and clear markdown sections.
- **Efficiency:** Optimizing for token usage and agent comprehension.

## 🤝 Contributing

Contributions are welcome! If you have a new skill to share or an improvement for an existing one:

1. Fork the repository.
2. Create a new branch for your feature.
3. Ensure your changes align with the `skill-mastery` guidelines.
4. Submit a Pull Request.

---
*Empowering AI agents with structured knowledge.*
