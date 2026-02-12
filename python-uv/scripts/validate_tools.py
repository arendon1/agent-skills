
import subprocess
import sys
import shutil

def check_tool(tool_name):
    """Check if a tool is available in the system PATH."""
    path = shutil.which(tool_name)
    if path:
        try:
            # Try to get the version to ensure it's executable
            result = subprocess.run([tool_name, "--version"], capture_output=True, text=True, check=True)
            print(f"✅ {tool_name} is installed: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError:
            print(f"⚠️ {tool_name} found at {path} but failed to execute.")
            return False
    else:
        print(f"❌ {tool_name} is NOT installed or not in PATH.")
        return False

def main():
    print("Validating python-uv skill environment...")
    
    uv_ok = check_tool("uv")
    ruff_ok = check_tool("ruff")
    
    if uv_ok and ruff_ok:
        print("\nAll required tools are present. Skill is ready to use.")
        sys.exit(0)
    else:
        print("\nMissing required tools. Please install them:")
        if not uv_ok:
            print("  - uv: curl -LsSf https://astral.sh/uv/install.sh | sh (or pip install uv)")
        if not ruff_ok:
            print("  - ruff: uv tool install ruff (or pip install ruff)")
        sys.exit(1)

if __name__ == "__main__":
    main()
