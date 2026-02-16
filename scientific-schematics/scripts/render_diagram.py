#!/usr/bin/env python3
import sys
import subprocess
import os
import shutil
from pathlib import Path

def check_command(cmd):
    return shutil.which(cmd) is not None

def run_mermaid_cli(input_file, output_prefix, theme="default"):
    """
    Renders a mermaid file to SVG and PNG using npx.
    """
    try:
        # Use shell=True for Windows compatibility with npx
        is_windows = os.name == 'nt'
        
        # 1. Render SVG
        svg_output = f"{output_prefix}.svg"
        print(f"[*] Rendering SVG: {svg_output}")
        subprocess.run(
            ["npx", "-p", "@mermaid-js/mermaid-cli", "mmdc", "-i", str(input_file), "-o", svg_output, "-t", theme, "-b", "transparent"],
            check=True, capture_output=True, text=True, shell=is_windows
        )
        
        # 2. Render PNG
        png_output = f"{output_prefix}.png"
        print(f"[*] Rendering PNG: {png_output}")
        subprocess.run(
            ["npx", "-p", "@mermaid-js/mermaid-cli", "mmdc", "-i", str(input_file), "-o", png_output, "-t", theme, "-b", "transparent", "-s", "2"],
            check=True, capture_output=True, text=True, shell=is_windows
        )
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Error rendering diagram: {e.stderr}")
        return False
    except Exception as e:
        print(f"[!] Unexpected error: {e}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python render_diagram.py <input.mmd> <output_name_no_ext> [theme]")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_prefix = sys.argv[2]
    theme = sys.argv[3] if len(sys.argv) > 3 else "default"

    if not input_file.exists():
        print(f"[!] Input file {input_file} not found.")
        sys.exit(1)

    # Check for Node/Npx
    if not check_command("node") or not check_command("npx"):
        print("[!] Node.js or npx not found in environment. Rendering skipped.")
        print("[!] You can still use the .mmd file in VS Code with the Mermaid extension.")
        sys.exit(0)

    success = run_mermaid_cli(input_file, output_prefix, theme)
    if success:
        print("[+] Diagram rendered successfully.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
