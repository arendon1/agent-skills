import os
import sys
import shutil
import json
from pathlib import Path

def get_platform_id() -> str:
    # Identify basic environment constraints
    if "CURSOR_APP_PATH" in os.environ or "CURSOR_CLI_PATH" in os.environ:
        return "Cursor"
    if "ANTHROPIC_TERM_ENV" in os.environ or "CLAUDE" in os.environ:
        return "Claude Code"
    if "GITHUB_ACTIONS" in os.environ:
        return "GitHub Actions"
    return "Unknown/Standard Terminal"

def check_cli(tool_name: str) -> bool:
    """Checks if a CLI tool is available in the system PATH."""
    return shutil.which(tool_name) is not None

def generate_env_file(workspace_root: Path):
    """
    Generates a .env file at the workspace root to inform agents of available tools.
    """
    env_vars = {
        "SF_AGENT_PLATFORM": get_platform_id(),
        "SF_PYTHON_EXEC": sys.executable,
        "SF_PYTHON_VERSION": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "SF_HAS_UV": str(check_cli("uv")).lower(),
        "SF_HAS_RUFF": str(check_cli("ruff")).lower(),
        "SF_HAS_JQ": str(check_cli("jq")).lower(),
        "SF_HAS_TLDR": str(check_cli("tldr")).lower(),
        "SF_HAS_RIPGREP": str(check_cli("rg")).lower()
    }

    env_path = workspace_root / ".env.skill-forge"
    
    env_content = "# skill-forge auto-generated environment tracking\n"
    for key, value in env_vars.items():
        env_content += f"{key}={value}\n"
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
        
    print(json.dumps({
        "status": "success",
        "env_path": str(env_path),
        "variables": env_vars
    }, indent=2))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=os.getcwd(), help="Path to the workspace root")
    args = parser.parse_args()
    
    generate_env_file(Path(args.workspace))
