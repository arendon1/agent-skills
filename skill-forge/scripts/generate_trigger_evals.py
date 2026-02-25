import sys
import json
from pathlib import Path


def generate_eval_template(skill_path: Path):
    """
    Given a skill directory, generates an empty but structured JSON
    eval file meant to be filled with 20 test cases (positive and negative)
    for optimizing the SKILL.md description.
    """
    skill_name = skill_path.name
    eval_file = skill_path / "evals" / "trigger_evals.json"

    # Ensure directory exists
    eval_file.parent.mkdir(parents=True, exist_ok=True)

    if eval_file.exists():
        print(f"Eval file already exists at {eval_file}")
        return

    # Generate a template
    template = []

    # 10 positive test cases
    for i in range(10):
        template.append(
            {
                "query": f"[Insert a realistic prompt where the user needs {skill_name}]",
                "should_trigger": True,
            }
        )

    # 10 negative test cases
    for i in range(10):
        template.append(
            {
                "query": f"[Insert a tricky prompt mentioning {skill_name} keywords but requiring a different tool/action]",
                "should_trigger": False,
            }
        )

    with open(eval_file, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2)

    print(f"✅ Generated eval template at {eval_file}")
    print(
        "Please fill out the 'query' strings with realistic triggers, then run `optimize_description.py`"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate an evaluation template for optimizing skill descriptions"
    )
    parser.add_argument("skill_dir", help="Path to the skill directory")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    if not skill_dir.is_dir():
        print(f"Error: {skill_dir} is not a directory.")
        sys.exit(1)

    generate_eval_template(skill_dir)
