"""
Usage export dispatcher — extracts usage data from LLM surfaces.

Usage:
    python scripts/export_usage.py --source opencode --output usage.json
    python scripts/export_usage.py --source opencode --db-path /path/to/db --output usage.json
    python scripts/export_usage.py --list-sources
    python scripts/export_usage.py --list-all
    python scripts/export_usage.py                                  # interactive
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridges import discover_bridges, discover_stubs


def _list_sources(bridges: dict, stubs: dict, include_stubs: bool = False) -> None:
    print("Available sources:\n")
    for name, mod in sorted(bridges.items()):
        help_text = getattr(mod, "SOURCE_HELP", "(no description)")
        print(f"  {name:<25} {help_text}")

    if include_stubs and stubs:
        print("\nPlanned (not yet implemented):\n")
        for name, help_text in sorted(stubs.items()):
            print(f"  {name:<25} {help_text}")


def _interactive_select(bridges: dict) -> str:
    names = sorted(bridges.keys())
    print("Available sources:\n")
    for i, name in enumerate(names, 1):
        mod = bridges[name]
        help_text = getattr(mod, "SOURCE_HELP", "")
        print(f"  [{i}] {name:<25} {help_text}")

    while True:
        try:
            choice = input(f"\nSelect source [1-{len(names)}]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(names):
                return names[idx]
        except (ValueError, KeyboardInterrupt):
            print("Cancelled.")
            sys.exit(1)
        print(f"Enter a number between 1 and {len(names)}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export LLM usage data from any supported surface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/export_usage.py --source opencode --output usage.json\n"
            "  python scripts/export_usage.py --source opencode --db-path /custom/path --output usage.json\n"
            "  python scripts/export_usage.py --list-sources\n"
            "  python scripts/export_usage.py                                     # interactive mode"
        ),
    )
    parser.add_argument("--source", "-s", help="Bridge name (e.g., opencode)")
    parser.add_argument("--output", "-o", help="Output file path (default: usage.json)")
    parser.add_argument("--list-sources", action="store_true", help="List available bridges")
    parser.add_argument("--list-all", action="store_true", help="List all bridges including future stubs")
    args, unknown = parser.parse_known_args()

    bridges = discover_bridges()
    stubs = discover_stubs()

    if args.list_sources or args.list_all:
        _list_sources(bridges, stubs, include_stubs=args.list_all)
        return

    source = args.source
    if not source:
        if not bridges:
            print("No bridges found. Check scripts/bridges/ directory.")
            sys.exit(1)
        source = _interactive_select(bridges)

    mod = bridges.get(source)
    if not mod:
        print(f"Error: Unknown source '{source}'.")
        print("Available sources:")
        for name in sorted(bridges.keys()):
            print(f"  - {name}")
        sys.exit(1)

    output_path = args.output or "usage.json"

    extra_kwargs: dict[str, str] = {}
    for i, arg in enumerate(unknown):
        if arg.startswith("--") and i + 1 < len(unknown):
            key = arg.lstrip("-").replace("-", "_")
            extra_kwargs[key] = unknown[i + 1]

    try:
        print(f"Extracting usage from {source}...")
        records = mod.extract(output_path, **extra_kwargs)
        print(f"Done: {len(records)} records written to {output_path}")
    except NotImplementedError:
        print(f"Source '{source}' is not yet implemented.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
