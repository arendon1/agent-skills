---
description: Improve or implement a skill with token efficiency and compliance to specifications
---

// turbo-all

1. **Discovery & Baseline Analysis**
   - Target: `./{{skill-name}}`
   - Use `list_dir` to find the skill folder. If it's a standalone `.md` file, prepare to scaffold it into a proper folder structure.
   - Inspect existing `SKILL.md` (if any), `scripts/`, and `references/`.
   - Identify if this is a "basic" definition that needs full implementation or an existing skill needing optimization.

2. **Synthesize Improvement Manifest with @[context-engineer]**
   - Reference `context-engineer/references/project-development.md` and `evaluation.md`.
   - Craft a specialized "Improvement Prompt" for `@skill-mastery` that includes:
     - **Refactoring Goals**: Specific patterns for moving logic from `SKILL.md` to `scripts/`.
     - **Token Targets**: Goals for reducing context overhead.
     - **Dependency Requirements**: Instructions on how the skill should self-manage environment setup.

3. **Execute Refactoring with @[skill-mastery]**
   - Pass the synthesized manifest to the `skill-mastery` logic.
   - Evaluate the baseline against the specification and apply the refactoring guidelines.
   - **Compliance Check**: Ensure metadata (name/description) and hierarchy load levels align with mastery standards.

4. **Implementation Plan Presentation**
   - Present the summarized blueprint to the user.
   - Highlight:
     - Predicted token savings.
     - New scripts to be created.
     - Dependency handling approach.
   - **WAIT for user approval** before proceeding.

5. **Refactoring & Implementation**
   - **Phase A (Structure)**: Scaffold the directory using `skillfish init` patterns if starting from scratch.
   - **Phase B (Optimization)**: Move heavy prose to `references/` and heavy logic to `scripts/`.
   - **Phase C (Logic)**: Implement or improve Python/Node scripts in `scripts/`. Ensure they are cross-platform compatible (forward slashes).
   - **Phase D (Frontmatter)**: Update `SKILL.md` with high-quality, trigger-rich descriptions and correct metadata.

6. **Final Validation & Compliance Check**
   - Run any available scripts in `scripts/validate.py` or similar if they exist.
   - Confirm the skill is ready for `skillfish` distribution.
   - Inform the user of any manual steps needed (e.g., setting environment variables).
