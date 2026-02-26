
import subprocess
import sys
import shutil
from pathlib import Path

def is_tool(name):
    """Check if tool is in PATH."""
    return shutil.which(name) is not None

def check_global():
    print("Checking global PATH for 'markitdown'...")
    if is_tool("markitdown"):
        path = shutil.which("markitdown")
        print(f"✅ Found global installation: {path}")
        return True
    print("❌ Not found in PATH.")
    return False

def check_local():
    print("Checking current Python environment for 'markitdown'...")
    try:
        import markitdown
        print(f"✅ Found in current site-packages: {markitdown.__file__}")
        return True
    except ImportError:
        print("❌ Not found in current site-packages.")
        return False

def setup_venv():
    print("Setting up local virtual environment using 'uv'...")
    try:
        # Check if uv is installed
        if not is_tool("uv"):
            print("❌ 'uv' not found. Please install uv (https://github.com/astral-sh/uv).")
            sys.exit(1)

        venv_path = Path(".venv")
        if not venv_path.exists():
            print("Creating .venv...")
            subprocess.run(["uv", "venv"], check=True)
        
        print("Installing 'markitdown[all]' via uv...")
        # Use the venv's pip or uv's direct pip interface
        subprocess.run(["uv", "pip", "install", "markitdown[all]"], check=True)
        
        print("✅ Installation complete.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        return False

def main():
    if check_local():
        print("Using current environment.")
        return 0
    
    if check_global():
        print("Using global installation.")
        return 0
    
    print("MarkItDown not found. Initiating setup...")
    if setup_venv():
        print("\nSUCCESS: MarkItDown is now available.")
        print("To use the local venv, ensure you activate it or use 'uv run markitdown'.")
        return 0
    else:
        print("\nERROR: Could not ensure MarkItDown installation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
