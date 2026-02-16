---
description: Audit a skill folder for compliance and security
---

// turbo-all

1. **Identify and Validate Target Folder**
   - Target: `./{{name-of-skill}}`
   - Use `list_dir` to verify the folder exists and inspect its contents (SKILL.md, scripts/, references/, etc.).
   - **Audit History Check**: Check for the existence and content of `.last_audit`.
     - If the last audit was within the last 24 hours, inform the user and ask if they want to proceed with a full re-audit or skip.
     - If the file is missing, proceed with the assumption this is the first primary audit.

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

4. **Deliver Structured Report & Update Log**
   - **Compliance Score**: [0-100%]
   - **Security Status**: [SECURE | AT RISK | VULNERABLE]
   - **Critical Vulnerabilities**: (List and block if any are found)
   - **Optimization Opportunities**: (List based on token hierarchy)
   - **Actionable Fixes**: Specific code/text replacements to resolve issues.
   - **Maintenance**: Upon successful delivery of the report, update the `.last_audit` file with the current date (YYYY-MM-DD).
