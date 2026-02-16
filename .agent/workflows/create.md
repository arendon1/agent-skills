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

2. **Synthesize Scaffolding Manifest with @[context-engineer]**
   - Once the user's idea is refined, use `@context-engineer/references/fundamentals.md` and `tools.md` to design the system.
   - Craft a specialized "Scaffolding Prompt" for `@skill-mastery` that includes:
     - **Architecture Spec**: Defining high-level logic vs. reference documentation.
     - **Interface Design**: Suggested `description` (trigger-rich) and tool usage.
     - **Resource Requirements**: Identifying necessary `scripts/` and `references/`.

3. **Execute Scaffolding with @[skill-mastery]**
   - Pass the synthesized manifest to the `skill-mastery` logic.
   - Use the `skillfish init` pattern to create the directory structure at the workspace root.
   - **Compliance Enforcement**: Ensure strict adherence to the Level 1-3 Token Hierarchy and frontmatter rules.

4. **Security & Compliance Check**
   - Ensure `SKILL.md` includes explicit safety guardrails if the skill performs destructive actions.
   - Validate that scripts avoid command injection and use safe path handling.

5. **Implementation & User Approval**
   - Present the initial scaffold and a drafted `SKILL.md` frontmatter.
   - **WAIT for user approval** before writing the full implementation of scripts.

6. **Post-Creation Maintenance**
   - Update `AGENTS.md` at the root to include the new skill's purpose and entry point.
   - Run a basic validation to ensure the skill is recognized.
