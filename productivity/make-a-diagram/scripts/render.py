#!/usr/bin/env python3
"""render.py — Render Mermaid diagrams to SVG, PNG, and ASCII formats.

Usage:
    python scripts/render.py <input.mmd> [--output-dir <dir>]

If --output-dir is omitted, defaults to docs/diagrams/ relative to
the detected workspace root (or current directory if not determinable).

Outputs:
    <name>.svg   — Vector (beautiful-mermaid)
    <name>.png   — Raster (mermaid-cli)
    <name>.txt   — ASCII art (beautiful-mermaid)
    <name>_log.json — Metadata + audit log

Dependencies:
    - Node.js + npx
    - @mermaid-js/mermaid-cli (for PNG)
    - beautiful-mermaid (for SVG + ASCII)
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def find_workspace_root() -> Path:
    """Walk up from cwd looking for .git or known workspace markers."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists():
            return parent
        if (parent / "README.md").exists() and (parent / ".vscode").exists():
            return parent
    return cwd


def check_deps():
    """Run check-deps.sh and exit if dependencies are missing."""
    script_dir = Path(__file__).resolve().parent
    check_script = script_dir / "check-deps.sh"
    if not check_script.exists():
        print("[render] Warning: check-deps.sh not found, skipping dependency check.")
        return
    result = subprocess.run(
        ["bash", str(check_script)],
        capture_output=True, text=True
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print("[render] Dependency check failed. Please install missing dependencies and retry.")
        sys.exit(1)


def run_mermaid_cli_svg(input_path: Path, output_path: Path) -> bool:
    """Render SVG using mermaid-cli (fallback: beautiful-mermaid SVG)."""
    cmd = [
        "npx", "--yes", "@mermaid-js/mermaid-cli", "mmd",
        "-i", str(input_path),
        "-o", str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[render] mermaid-cli SVG failed: {result.stderr}")
        return False
    return True


def run_mermaid_cli_png(input_path: Path, output_path: Path) -> bool:
    """Render PNG using mermaid-cli."""
    cmd = [
        "npx", "--yes", "@mermaid-js/mermaid-cli", "mmd",
        "-i", str(input_path),
        "-o", str(output_path),
        "-b", "png",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[render] mermaid-cli PNG failed: {result.stderr}")
        return False
    return True


def run_beautiful_ascii(input_path: Path, output_path: Path) -> bool:
    """Render ASCII art using beautiful-mermaid via Node.js."""
    script_dir = Path(__file__).resolve().parent
    wrapper_script = script_dir / "render_beautiful.mjs"

    if not wrapper_script.exists():
        print("[render] render_beautiful.mjs not found, skipping ASCII output.")
        return False

    cmd = [
        "node", str(wrapper_script),
        "ascii",
        str(input_path),
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[render] beautiful-mermaid ASCII failed: {result.stderr.strip()}")
        return False
    return True


def run_beautiful_svg(input_path: Path, output_path: Path) -> bool:
    """Render SVG using beautiful-mermaid (higher quality than mermaid-cli)."""
    script_dir = Path(__file__).resolve().parent
    wrapper_script = script_dir / "render_beautiful.mjs"

    if not wrapper_script.exists():
        print("[render] render_beautiful.mjs not found, falling back to mermaid-cli SVG.")
        return False

    cmd = [
        "node", str(wrapper_script),
        "svg",
        str(input_path),
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[render] beautiful-mermaid SVG failed: {result.stderr.strip()}")
        return False
    return True


def write_log(output_dir: Path, name: str, svg_ok: bool, png_ok: bool, ascii_ok: bool, source: str):
    """Write metadata + audit log."""
    log_path = output_dir / f"{name}_log.json"
    log_data = {
        "name": name,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "outputs": {
            "svg": {"status": "ok" if svg_ok else "failed", "path": str(output_dir / f"{name}.svg")},
            "png": {"status": "ok" if png_ok else "failed", "path": str(output_dir / f"{name}.png")},
            "txt": {"status": "ok" if ascii_ok else "failed", "path": str(output_dir / f"{name}.txt")},
        },
        "renderer": {
            "svg": "beautiful-mermaid (fallback: mermaid-cli)",
            "png": "@mermaid-js/mermaid-cli",
            "ascii": "beautiful-mermaid",
        }
    }
    log_path.write_text(json.dumps(log_data, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Render Mermaid diagrams to SVG, PNG, and ASCII.")
    parser.add_argument("input", type=str, help="Path to .mmd source file")
    parser.add_argument("--output-dir", "-o", type=str, default=None,
                        help="Output directory (default: <workspace_root>/docs/diagrams/)")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if input_path.suffix != ".mmd":
        print("Warning: Input file does not have .mmd extension.", file=sys.stderr)

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        workspace_root = find_workspace_root()
        output_dir = workspace_root / "docs" / "diagrams"

    output_dir.mkdir(parents=True, exist_ok=True)

    name = input_path.stem

    # Check dependencies
    check_deps()

    # Render
    print(f"[render] Processing: {input_path.name}")
    print(f"[render] Output:   {output_dir}")

    svg_ok = run_beautiful_svg(input_path, output_dir / f"{name}.svg")
    if not svg_ok:
        print("[render] Falling back to mermaid-cli for SVG...")
        svg_ok = run_mermaid_cli_svg(input_path, output_dir / f"{name}.svg")

    png_ok = run_mermaid_cli_png(input_path, output_dir / f"{name}.png")
    ascii_ok = run_beautiful_ascii(input_path, output_dir / f"{name}.txt")

    # Write audit log
    write_log(output_dir, name, svg_ok, png_ok, ascii_ok, str(input_path))

    # Summary
    print("")
    print("=== Render Summary ===")
    print(f"  SVG:   {'OK' if svg_ok else 'FAILED'}")
    print(f"  PNG:   {'OK' if png_ok else 'FAILED'}")
    print(f"  ASCII: {'OK' if ascii_ok else 'FAILED'}")
    print(f"  Log:   {output_dir / f'{name}_log.json'}")

    if not (svg_ok or png_ok or ascii_ok):
        print("[render] No outputs were generated. Check dependency installation.")
        sys.exit(1)


if __name__ == "__main__":
    main()
