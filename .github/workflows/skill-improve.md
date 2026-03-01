---
description: Execute Test-Driven Development loops to optimize a skill's description and test its agentic compliance against baselines
---
## Improving a Skill

1. **Trigger Evals**: Run `python c:/Users/andres.rendon/Documents/Prompts/skills/skill-forge/scripts/generate_trigger_evals.py <path-to-skill>`. Review the generated 20 test cases (positive + negative) with the user.
2. **Optimize Description**: Run `python c:/Users/andres.rendon/Documents/Prompts/skills/skill-forge/scripts/optimize_description.py <path-to-skill> --eval-set <eval.json>`. Ensure you pass your session's model ID so the triggers test against the actual active model.
3. **Behavioral Benchmarking**: Run `python c:/Users/andres.rendon/Documents/Prompts/skills/skill-forge/scripts/run_benchmark.py <path-to-skill> --iterations 1`. This will spawn parallel baseline agents and evaluate them against grading assertions.
4. **Iterative Refinement**: Rewrite the rules in `SKILL.md` based on the benchmarking failures, aiming to close agent loopholes, and re-run.
