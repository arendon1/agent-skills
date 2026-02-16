---
description: Audit a skill folder for compliance and security
---

// turbo-all

1. **Identify and Validate Target Folder**
   - Target: `./{{name-of-skill}}`
   - Use `list_dir` to verify the folder exists and inspect its contents (SKILL.md, scripts/, references/, etc.).

2. **Synthesize Audit Prompt with @[context-engineer]**
   - Reference `context-engineer/references/evaluation.md` and `tools.md`.
   - Create a specialized "Audit Manifest" prompt that defines high-fidelity evaluation rubrics for:
     - **Security**: Threat modeling of scripts, credential leakage detection, and execution safety.
     - **Compliance**: Adherence to the `skill-mastery` specification (frontmatter, token hierarchy, progressive disclosure).
     - **Efficiency**: Token usage optimization and description quality.

3. **Execute Audit with @[skill-mastery]**
   - Pass the synthesized prompt to the `skill-mastery` logic.
   - Perform a line-by-line audit of `SKILL.md` and a code review of any files in `scripts/`.
   - Explicitly look for security breaches: command injection (`os.system`, `subprocess` with `shell=True`), path traversal, and hardcoded secrets.

4. **Deliver Structured Report**
   - **Compliance Score**: [0-100%]
   - **Security Status**: [SECURE | AT RISK | VULNERABLE]
   - **Critical Vulnerabilities**: (List and block if any are found)
   - **Optimization Opportunities**: (List based on token hierarchy)
   - **Actionable Fixes**: Specific code/text replacements to resolve issues.
