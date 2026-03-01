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
2. **skillfish Integration**: The script automatically initializes a `skillfish.json` manifest.
3. **Document Triggers**: Edit the newly created `SKILL.md` and focus completely on the `description` block inside the frontmatter. Ensure you answer "Use when...", not "What this does".
4. **Draft Instructions**: Write the actual instructional prose inside `SKILL.md`, adhering to the maximum 500-line token constraint.
""",
    "skill-audit": """---
description: Validate a skill's token efficiency, check structural compliance, and perform a security scan
---
## Auditing a Skill

1. **Invoke Validation**: Run `python {forge_script_dir}/validate_and_audit.py <path-to-skill>`
2. **Review Violations**: The script will check if `SKILL.md` is too long, if description rules are followed, and if **`skillfish.json`** is present and valid.
3. **Security Scan**: The validation also statically analyzes the `scripts/` directory for obvious bad security practices, exploits, or malware.
""",
    "skill-package": """---
description: Zip one or many skills for sharing or distribution
---
## Packaging Skills

1. **Invoke Packaging**: Run `python {forge_script_dir}/package_skills.py <path-to-skill1> [path-to-skill2] ...`
2. **Distribution Options**:
   - Use `--bundle` to update the project's `skillfish.json` manifest.
   - Use `--submit <repo>` to register your skills on skill.fish.
3. **Collect Artifacts**: Generated `.zip` files will be in the `dist/` folder.
""",
    "skill-improve": """---
description: Execute Test-Driven Development loops to optimize a skill's description and test its agentic compliance against baselines
---
## Improving a Skill

1. **Trigger Evals**: Run `python {forge_script_dir}/generate_trigger_evals.py <path-to-skill>`. Review the generated 20 test cases.
2. **Optimize Description**: Run `python {forge_script_dir}/optimize_description.py <path-to-skill> --eval-set <eval.json>`.
3. **Behavioral Benchmarking**: Run `python {forge_script_dir}/run_benchmark.py <path-to-skill> --iterations 1`.
4. **Iterative Refinement**: Rewrite the rules in `SKILL.md` based on benchmarking failures and re-run.
""",
    "skill-manage": """---
description: Browse, list, update, or remove skills using the skillfish engine
---
## Managing Skills

1. **Inventory**: Run `python {forge_script_dir}/skill_manager.py list` to see installed skills.
2. **Registry Search**: Run `python {forge_script_dir}/skill_manager.py search <query>`.
3. **Maintenance**: Run `python {forge_script_dir}/skill_manager.py update` to keep skills fresh.
4. **Removal**: Run `python {forge_script_dir}/skill_manager.py remove <skill>` to clean up.
""",
    "skill-sync": """---
description: Synchronize environment with the project's skillfish.json manifest
---
## Syncing Skills

1. **Manifest Sync**: Run `python {forge_script_dir}/skill_manager.py sync --project`.
2. **Verification**: After syncing, run `/skill-manage list` to confirm consistency.
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
