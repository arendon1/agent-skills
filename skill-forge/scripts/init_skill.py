import sys
from pathlib import Path


def generate_frontmatter(name: str) -> str:
    """Generates GF(3) compliant frontmatter with placeholder triggers"""
    return f"""---
name: {name}
description: >-
  [What it does - actions, capabilities].
  Use when [trigger phrases, contexts, file types].
metadata:
  version: "1.0.0"
  language: en # alternatives: es-CO
  trit: 0
  risk_tier: CAUTION
---

# {name}

## When to Use

- [Symptom 1]
- [Symptom 2]

## Core Pattern

```bash
# Add your core instructional patterns here
```

## Quick Reference

| Action | Command |
| ------ | ------- |
| Do X   | `run X` |

"""


def init_skill(skill_name: str, target_dir: Path):
    """
    Scaffolds the directory structure for a new skill.
    Enforces the Token Loading Hierarchy.
    """
    skill_dir = target_dir / skill_name

    if skill_dir.exists():
        print(f"Error: Directory {skill_dir} already exists.")
        sys.exit(1)

    skill_dir.mkdir(parents=True)

    # Create Token Loading Hierarchy Dirs
    (skill_dir / "scripts").mkdir()
    (skill_dir / "references").mkdir()
    (skill_dir / "examples").mkdir()
    (skill_dir / "evals").mkdir()

    # Write main SKILL.md
    with open(skill_dir / "SKILL.md", "w", encoding="utf-8") as f:
        f.write(generate_frontmatter(skill_name))

    # skillfish integration
    print(f"🐟 Initializing skillfish manifest...")
    try:
        import subprocess

        # skillfish init --project needs an agent folder to detect
        agent_dir = skill_dir / ".agent"
        agent_dir.mkdir(exist_ok=True)

        subprocess.run(
            [
                "skillfish",
                "init",
                "--name",
                skill_name,
                "--description",
                f"A skill-forge skill: {skill_name}",
                "--yes",
                "--project",
            ],
            cwd=skill_dir,
            check=True,
            capture_output=True,
            text=True,
            shell=True,
        )
        print(f"✅ Created skillfish.json in {skill_dir}")
    except Exception as e:
        print(f"⚠️ Warning: skillfish init failed: {e}")

    print(f"✅ Created core structure for {skill_name}")
    print(f"   Docs:     {skill_dir}/SKILL.md")
    print(f"   Context:  {skill_dir}/references/")
    print(f"   Logic:   {skill_dir}/scripts/")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("Scaffold a unified skill-forge compliant skill")
    parser.add_argument("name", help="Name of the skill (lowercase, hyphens)")
    parser.add_argument("--path", required=True, help="Destination directory path")
    args = parser.parse_args()

    init_skill(args.name, Path(args.path))
