#!/usr/bin/env python3
"""Universal bootstrapping script for AI agent skills.

This script ensures that a skill's workflows and rules are correctly
deployed to the user's workspace so the local agent can discover them.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# Standard agent configuration directories
AGENT_DIRS = [
    ".agent/workflows",
    ".agents/workflows",
    ".cursor/rules",
    ".gemini/configs",
    ".github/workflows",
]


def find_workspace_root(cwd: Path) -> Path:
    """Find the workspace root by looking for common markers."""
    markers = [".git", ".agent", ".agents", "skillfish.json"]
    current = cwd
    for parent in [current, *current.parents]:
        if any((parent / m).exists() for m in markers):
            return parent
    return current


def bootstrap_skill(skill_path: Path, workspace_root: Path, force: bool = False):
    """Deploy workflows from the skill path to the workspace root."""
    workflow_src = skill_path / ".agent" / "workflows"
    if not workflow_src.exists():
        workflow_src = skill_path / "workflows"  # Fallback

    if not workflow_src.exists():
        print(f"No workflow source found in {skill_path}. Skipping deployment.")
        return

    # Identify existing agent directories in the workspace
    found_dirs = []
    for d in AGENT_DIRS:
        target = workspace_root / d
        if target.exists():
            found_dirs.append(target)

    # If no directories found, default to .agent/workflows
    if not found_dirs:
        default_dir = workspace_root / ".agent" / "workflows"
        default_dir.mkdir(parents=True, exist_ok=True)
        found_dirs.append(default_dir)
        print(f"No agent structure detected. Defaulting to {default_dir}")

    # Copy files
    deployed_count = 0
    for target_dir in found_dirs:
        for src_file in workflow_src.glob("*.md"):
            dest_file = target_dir / src_file.name
            if dest_file.exists() and not force:
                continue

            shutil.copy2(src_file, dest_file)
            deployed_count += 1
            print(
                f"Deployed: {src_file.name} -> {target_dir.relative_to(workspace_root)}"
            )

    print(
        f"Bootstrap complete. {deployed_count} files deployed across {len(found_dirs)} directories."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap a skill into the current workspace"
    )
    parser.add_argument("--skill-path", default=".", help="Path to the skill directory")
    parser.add_argument(
        "--workspace", default=None, help="Force a specific workspace root"
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing workflows"
    )
    args = parser.parse_args()

    skill_path = Path(args.skill_path).absolute()
    workspace_root = (
        Path(args.workspace).absolute()
        if args.workspace
        else find_workspace_root(Path.cwd())
    )

    print(f"Bootstrapping skill from: {skill_path}")
    print(f"Workspace root detected: {workspace_root}")

    bootstrap_skill(skill_path, workspace_root, args.force)


if __name__ == "__main__":
    main()
