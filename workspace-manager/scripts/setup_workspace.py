import os
import sys
import json
import shutil
from pathlib import Path


def setup_workspace(target_dir, skill_dir):
    target = Path(target_dir).resolve()
    skill = Path(skill_dir).resolve()

    print(f"🚀 Initializing workspace at: {target}")

    # 1. Create .agent hierarchy
    agent_dirs = [
        ".agent/workflows",
        ".agent/skills",
        ".agent/rules",
        ".agent/specs",
        ".agent/steering",
        ".agent/hooks",
    ]
    for d in agent_dirs:
        (target / d).mkdir(parents=True, exist_ok=True)
        print(f"  - Created {d}")

    # 2. Create .vscode/settings.json
    vscode_dir = target / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    settings_file = vscode_dir / "settings.json"
    if not settings_file.exists():
        settings = {
            "files.exclude": {
                "**/.git": True,
                "**/.DS_Store": True,
                "**/Thumbs.db": True,
                "**/.agent": False,
            },
            "editor.formatOnSave": True,
            "editor.rule": [80, 100, 120],
        }
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=4)
        print("  - Created .vscode/settings.json")

    # 3. Create basic files
    basic_files = {
        ".gitignore": "# IDEs\n.vscode/\n.idea/\n\n# Orphands\n.review/\n\n# Agents\n.agent/skills/*\n!.agent/skills/.keep\n",
        "README.md": f"# {target.name}\n\nProject initialized with workspace-manager.",
        "docs/ARCHITECTURE.md": "# Architecture Overview\n\nDocument your system architecture here.",
    }

    for filename, content in basic_files.items():
        file_path = target / filename
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
            print(f"  - Created {filename}")

    # 4. Deploy Workflows from Skill to Workspace
    workflow_src = skill / "templates" / "workflows"
    workflow_dest = target / ".agent" / "workflows"

    if workflow_src.exists():
        for wf in workflow_src.glob("*.md"):
            shutil.copy(wf, workflow_dest)
            print(f"  - Deployed workflow: {wf.name}")
    else:
        print("  ! No workflow templates found in skill directory to deploy.")

    # 5. Create .agent/skills/.keep to allow tracking the folder but ignoring contents
    (target / ".agent/skills/.keep").touch()

    print("\n✅ Workspace initialized successfully!")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    # Assume script is in scripts/ folder of the skill
    skill_dir = Path(__file__).resolve().parent.parent
    setup_workspace(target, skill_dir)
