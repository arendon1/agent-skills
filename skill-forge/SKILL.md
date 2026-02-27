---
name: skill-forge
description: >-
  The definitive framework for creating, optimizing, and auditing AI agent skills.
  Combines Test-Driven Development loops with strict architectural validation.
  Use when creating a new skill, improving an existing skill's trigger rate,
  benchmarking agent performance, or auditing a skill for structural/security issues.
metadata:
  version: "1.0.0"
  trit: 0
  risk_tier: CAUTION
---

# skill-forge: United Skill Development Framework

**`skill-forge`** merges the architectural rigor of Token Loading Hierarchies with the empirical validation of Test-Driven agent workflows. It explicitly offloads heavy processing into deterministic Python scripts to prevent LLM context rot.

## The 4 Core Principles

1. **Token Hierarchy Efficiency**: Only the `name` and `description` are loaded globally. `SKILL.md` is loaded conditionally. `references/` are loaded on-demand.
2. **Deterministic Process Logic**: We do not let agents "guess" how to test or validate skills. We execute python scripts to execute parallel baselines.
3. **GF(3) / Triadic Classification**: Skills must declare their ontological purpose (`+1` generation, `-1` constraint, `0` mediation).
4. **Environment Awareness**: Scripts dynamically adapt to Cursor, Claude Code, GitHub Actions, or local terminals.
5. **Language Consistency**: Skills must be written ENTIRELY in English (`en`) or Spanish (`es-CO`). No mixing of languages is permitted within a single skill.

## Command Glossary (Project-Level Slash Workflows)

You should manage skills by invoking the project-level slash workflows (which were generated globally by `scripts/deploy_slash_workflows.py`).

Do not try to "manually" write validation algorithms. **Use the scripts.**

### 1. `/skill-create` (Initialization)

Use this workflow to scaffold a brand new, structurally flawless skill directory.

- **Behind the scenes**: It runs `scripts/init_skill.py`.
- **Next steps**: Focus entirely on polishing the `description` string. It must start with "Use when..." and explain the *triggering symptoms*, not the process. Keep the `SKILL.md` under 500 lines.

### 2. `/skill-improve` (Empirical TDD Optimization)

Use this workflow to optimize a skill that is under-triggering or logically flawed.

- **Behind the scenes**:
  1. `scripts/generate_trigger_evals.py` (Drafts 20 positive/negative trigger cases).
  2. `scripts/optimize_description.py` (Iteratively trains the `description` YAML).
  3. `scripts/run_benchmark.py` (Spawns a parallel "with skill" vs "without skill" agent to measure Time, Tokens, and Pass Rate).
- **Next steps**: Rewrite the `SKILL.md` rules based on the specific rationalizations the agents used to fail the baseline benchmark.

### 3. `/skill-audit` (Validation and Security)

Use this workflow before finalizing a skill.

- **Behind the scenes**: It runs `scripts/validate_and_audit.py`.
- **What it checks**:
  - `SKILL.md` length (<500 lines).
  - Third-party prompt formatting ("Use when...").
  - Reference folder depth (max 1 level deep).
  - **Language Audit**: Verifies that the skill is either English or Spanish and remains consistent throughout.
  - **Security Scan**: Statically analyzes `scripts/` for obvious bad practices (e.g., unfiltered `os.system()`, `eval()`).

### 4. `/skill-package` (Distribution)

Use this workflow to zip one or many skills for sharing or distribution.

- **Behind the scenes**: It runs `scripts/package_skills.py`.
- **Functionality**:
  - Packages the entire skill directory into a `.skill` (ZIP) format.
  - Supports multiple skill paths at once.
  - Automatically excludes junk like `__pycache__` and `.git`.
- **Result**: Retrieve the generated archives from the `dist/` directory.

## Required Skill Frontmatter

Every skill created by the forge must use this generalized frontmatter schema:

```yaml
---
name: [lowercase-with-hyphens]
description: >-
  [What it does briefly].
  Use when [Specific trigger phrases, contexts, error symptoms, file types].
metadata:
  version: "1.0.0"
  language: en # Options: en, es-CO
  trit: [1, 0, or -1]
  risk_tier: [CRITICAL, DANGEROUS, CAUTION]
---
```

## Further Reading (On-Demand References)

If you need deeper context, read the following files located in `references/`:

- `references/archetypes.md`: Standard structural blueprints (CLI Reference, Methodology, Safety, Orchestration).
- `references/token-hierarchy.md`: The calculus of how LLMs load skill context.
- `references/schemas.md`: JSON structures for Test-Driven evaluations.
- `references/testing-methodology.md`: The RED-GREEN-REFACTOR doctrine for documentation.

**Remember**: Let Python handle the loops. Your job is writing excellent, airtight prose in `SKILL.md`.
