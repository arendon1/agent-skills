---
description: Interactive scaffolding of a new skill from a vague idea
---

// turbo-all

1. **Idea Extraction & Interactive Refinement**
   - Start an interactive dialogue with the user to expand on the vague idea: `{{vague-idea}}`.
   - Ask clarifying questions to determine:
     - **Goal**: What specific problem does this skill solve?
     - **Trigger**: When should the agent decide to use this skill?
     - **Archetype**: Is it a CLI Reference, Methodology, Safety Tool, or Orchestration skill?
     - **Logic**: What parts require Python/Node scripts vs. LLM reasoning?

2. **Conceptual Blueprinting with @[context-engineer]**
   - Once the idea is solid, use `@context-engineer/references/fundamentals.md` and `tools.md` to design the system.
   - Output a "Skill Design Spec" including:
     - **Name**: `[a-z0-9-]+` compliant name.
     - **Description**: Target <1024 chars, focusing on trigger phrases.
     - **Resource Plan**: List of required scripts in `scripts/` and docs in `references/`.

3. **Scaffolding with @[skill-mastery]**
   - Use the `skillfish init` pattern described in `@[skill-mastery]` to create the directory at the workspace root.
   - **Structure**:
     - `{{skill-name}}/SKILL.md` (Core instructions with Token Loading Hierarchy Level 2).
     - `{{skill-name}}/scripts/` (Logic/Automation).
     - `{{skill-name}}/references/` (Deep-dive documentation).
     - `{{skill-name}}/examples/` (Concrete usage samples).

4. **Security & Compliance Check**
   - Ensure `SKILL.md` includes explicit safety guardrails if the skill performs destructive actions.
   - Validate that scripts avoid command injection and use safe path handling.

5. **Implementation & User Approval**
   - Present the initial scaffold and a drafted `SKILL.md` frontmatter.
   - **WAIT for user approval** before writing the full implementation of scripts.

6. **Post-Creation Maintenance**
   - Update `AGENTS.md` at the root to include the new skill's purpose and entry point.
   - Run a basic validation to ensure the skill is recognized.
