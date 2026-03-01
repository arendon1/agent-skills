import argparse
import subprocess
import sys
from pathlib import Path


def run_skillfish(args):
    """Executes a skillfish command and prints the result"""
    cmd = ["skillfish"] + args
    print(f"🐟 Executing: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, text=True, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing skillfish: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Unified Skill Manager for skill-forge (powered by skillfish)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # List
    subparsers.add_parser("list", help="List installed skills")

    # Search
    search_parser = subparsers.add_parser("search", help="Search the skill registry")
    search_parser.add_argument("query", help="Search term")

    # Update
    subparsers.add_parser("update", help="Update all installed skills")

    # Remove
    remove_parser = subparsers.add_parser("remove", help="Remove an installed skill")
    remove_parser.add_argument("skill", help="Name of the skill to remove")

    # Sync/Install
    sync_parser = subparsers.add_parser(
        "sync", help="Sync skills from skillfish.json manifest"
    )
    sync_parser.add_argument(
        "--project", action="store_true", help="Sync from project manifest"
    )

    # Bundle
    subparsers.add_parser(
        "bundle", help="Generate skillfish.json from installed skills"
    )

    args = parser.parse_args()

    if args.command == "list":
        run_skillfish(["list"])
    elif args.command == "search":
        run_skillfish(["search", args.query])
    elif args.command == "update":
        run_skillfish(["update"])
    elif args.command == "remove":
        run_skillfish(["remove", args.skill])
    elif args.command == "sync":
        cmd_args = ["install"]
        if args.project:
            cmd_args.append("--project")
        run_skillfish(cmd_args)
    elif args.command == "bundle":
        run_skillfish(["bundle"])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
