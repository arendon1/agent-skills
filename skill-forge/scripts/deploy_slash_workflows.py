import os
from pathlib import Path

# The standard directories where AI agents look for workflow/rule context
TARGET_WORKFLOW_DIRS = [
    ".agents/workflows",
    ".cursor/rules",
    ".github/workflows",
    ".gemini/workflows",
]

WORKFLOW_TEMPLATES = {
    "skill-create": """---
description: Scaffold a new skill directory using the strict skill-forge standard
---
## Creating a New Skill

1. **Invoke Initialization**: Run `python {forge_script_dir}/init_skill.py <skill-name> --path <destination>`
2. **Document Triggers**: Edit the newly created `SKILL.md` and focus completely on the `description` block inside the frontmatter. Ensure you answer "Use when...", not "What this does".
3. **Reference Generation**: Populate any heavy references in `references/` one level deep. Do not nest directories.
4. **Draft Instructions**: Write the actual instructional prose inside `SKILL.md`, adhering to the maximum 500-line token constraint.
""",
    "skill-audit": """---
description: Validate a skill's token efficiency, check structural compliance, and perform a security scan
---
## Auditing a Skill

1. **Invoke Validation**: Run `python {forge_script_dir}/validate_and_audit.py <path-to-skill>`
2. **Review Violations**: The script will check if `SKILL.md` is over 500 lines, if references are nested too deeply, or if the description misses the "Use when..." directive.
3. **Security Scan**: The validation also statically analyzes the `scripts/` directory for obvious bad security practices, exploits, or malware.
""",
    "skill-package": """---
description: Zip one or many skills for sharing or distribution
---
## Packaging Skills

1. **Identify Skills**: Collect the directory paths of the skills you want to package.
2. **Execute Packaging**: Run `python {forge_script_dir}/package_skills.py <path-to-skill1> [path-to-skill2] ...`
3. **Optional Output**: You can specify an output directory with `--out <dir>`.
4. **Collect Artifacts**: The scripts will generate `.skill` (ZIP) files in the `dist/` folder (or your specified output dir).
""",
    "skill-improve": """---
description: Execute Test-Driven Development loops to optimize a skill's description and test its agentic compliance against baselines
---
## Improving a Skill

1. **Trigger Evals**: Run `python {forge_script_dir}/generate_trigger_evals.py <path-to-skill>`. Review the generated 20 test cases (positive + negative) with the user.
2. **Optimize Description**: Run `python {forge_script_dir}/optimize_description.py <path-to-skill> --eval-set <eval.json>`. Ensure you pass your session's model ID so the triggers test against the actual active model.
3. **Behavioral Benchmarking**: Run `python {forge_script_dir}/run_benchmark.py <path-to-skill> --iterations 1`. This will spawn parallel baseline agents and evaluate them against grading assertions. 
4. **Iterative Refinement**: Rewrite the rules in `SKILL.md` based on the benchmarking failures, aiming to close agent loopholes, and re-run.
""",
}


def setup_slash_commands(workspace_root: Path, forge_script_dir: Path):
    """
    Creates agent workflow files across all recognized agent configuration directories
    found in the workspace root.
    """
    deployed_files = []

    for relative_dir in TARGET_WORKFLOW_DIRS:
        target_dir = workspace_root / relative_dir

        # Only deploy if the structural parent already exists, or if we force create it.
        # We will dynamically create the dirs just in case to assure global coverage.
        target_dir.mkdir(parents=True, exist_ok=True)

        for workflow_name, template in WORKFLOW_TEMPLATES.items():
            ext = ".mdc" if "cursor" in relative_dir else ".md"
            filepath = target_dir / f"{workflow_name}{ext}"

            # Format the string to include the absolute path to our skill-forge python scripts
            content = template.format(
                forge_script_dir=str(forge_script_dir.absolute()).replace("\\", "/")
            )

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            deployed_files.append(str(filepath))

    print(f"Deployment complete. Generated {len(deployed_files)} workflow files.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace", default=os.getcwd(), help="Path to the workspace root"
    )
    parser.add_argument(
        "--forge-scripts",
        required=True,
        help="Path to the skill-forge scripts directory",
    )
    args = parser.parse_args()

    setup_slash_commands(Path(args.workspace), Path(args.forge_scripts))
