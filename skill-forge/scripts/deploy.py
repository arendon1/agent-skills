#!/usr/bin/env python3
"""Deploy skill-forge slash-commands to agent directories.

Detects available agents (Antigravity, OpenCode, Copilot, Kiro) and deploys
slash-commands to appropriate directories.
"""

import os
import shutil
from pathlib import Path


AGENT_DIRS = {
    "universal": ".agents/skills",
    "kiro": ".kiro/skills",
}

AGENT_TOOLS = ["antigravity", "opencode", "copilot", "kiro"]


def detect_agents() -> dict[str, bool]:
    """Detect which agents are available in the system."""
    return {agent: shutil.which(agent) is not None for agent in AGENT_TOOLS}


WORKFLOW_TEMPLATES = {
    "skill-create": """---
description: Scaffold a new skill directory using the skill-forge standard
---
## Creating a New Skill

1. **Invoke Initialization**: Run `python {forge_script_dir}/init.py <skill-name> --path <destination>`
2. **Document Triggers**: Edit the newly created `SKILL.md` and focus on the `description` block. Ensure you answer "Use when...", not "What this does".
3. **Draft Instructions**: Write the instructional prose inside `SKILL.md`, keeping it under 500 lines.
""",
    "skill-audit": """---
description: Validate a skill's structure, description format, and security
---
## Auditing a Skill

1. **Run Audit**: Execute `python {forge_script_dir}/audit.py <path-to-skill>`
2. **Review Output**: The script outputs an XML prompt. Present this to a subagent capable of running the audit checks.
3. **Apply Fixes**: Based on the audit results, update `SKILL.md` accordingly.
""",
    "skill-improve": """---
description: Optimize a skill using Test-Driven Development
---
## Improving a Skill (TDD)

1. **Run TDD Loop**: Present the XML prompt from `audit.py` to a subagent. The agent spawns additional subagents internally to run different models against test cases.
2. **Understand Output**: The script outputs a single XML prompt containing test cases and improvement criteria.
3. **Execute Loop**: Present the XML to a subagent. The agent spawns additional subagents internally to run different models against test cases.
4. **Iterate**: The agent runs the TDD loop until all tests pass or max iterations reached.
5. **Result**: Updated `SKILL.md` with optimized description.
""",
}


def setup_slash_commands(workspace_root: Path, forge_script_dir: Path):
    """Deploy slash-commands to all available agent directories."""
    detected = detect_agents()
    available = [a for a, present in detected.items() if present]

    if available:
        print(f"Detected agents: {', '.join(available)}")
    else:
        print("Warning: No agent CLIs detected (antigravity, opencode, copilot, kiro)")

    deployed_files = []

    for scope, rel_path in AGENT_DIRS.items():
        target_dir = workspace_root / rel_path
        target_dir.mkdir(parents=True, exist_ok=True)

        for workflow_name, template in WORKFLOW_TEMPLATES.items():
            filepath = target_dir / f"{workflow_name}.md"
            content = template.format(
                forge_script_dir=str(forge_script_dir.absolute()).replace("\\", "/")
            )
            filepath.write_text(content, encoding="utf-8")
            deployed_files.append(str(filepath))

    print(f"Deployment complete. Generated {len(deployed_files)} workflow files.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deploy skill-forge slash-commands to agent directories")
    parser.add_argument("--workspace", default=os.getcwd(), help="Path to the workspace root")
    parser.add_argument("--forge-scripts", required=True, help="Path to the skill-forge scripts directory")

    args = parser.parse_args()
    setup_slash_commands(Path(args.workspace), Path(args.forge_scripts))