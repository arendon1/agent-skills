import os
import re
import sys


def analyze_workspace(root_dir):
    """
    Heuristically identifies the existing directory structure and naming patterns.
    """
    structure = {}
    patterns = {
        "kebab-case": 0,
        "snake_case": 0,
        "camelCase": 0,
        "PascalCase": 0,
        "space-separated": 0,
    }

    for root, dirs, files in os.walk(root_dir):
        # Exclude hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        rel_path = os.path.relpath(root, root_dir)
        if rel_path == ".":
            structure["root"] = dirs
        else:
            structure[rel_path] = dirs

        for name in dirs + files:
            if " " in name:
                patterns["space-separated"] += 1
            if re.match(r"^[a-z0-9]+(-[a-z0-9]+)*(\.[a-z0-9]+)?$", name):
                patterns["kebab-case"] += 1
            elif re.match(r"^[a-z0-9]+(_[a-z0-9]+)*(\.[a-z0-9]+)?$", name):
                patterns["snake_case"] += 1
            elif re.match(r"^[a-z][a-zA-Z0-9]*(\.[a-z0-9]+)?$", name):
                patterns["camelCase"] += 1
            elif re.match(r"^[A-Z][a-zA-Z0-9]*(\.[a-z0-9]+)?$", name):
                patterns["PascalCase"] += 1

    # Determine dominant pattern
    dominant_pattern = (
        max(patterns, key=patterns.get) if any(patterns.values()) else "unknown"
    )

    return structure, dominant_pattern


def generate_project_md(structure, dominant_pattern):
    """
    Generates a PROJECT.md content based on the identified structure.
    """
    content = "# Project Structure & Standards\n\n"
    content += "## Identified Structure\n\n"

    # Show main directories
    if "root" in structure:
        content += "The following core directories define the workspace structure:\n"
        for d in structure["root"]:
            content += f"- `{d}/`\n"

    content += "\n## Naming Conventions\n\n"
    content += f"- **Dominant Pattern**: `{dominant_pattern}`\n"
    content += "- **Rule**: All new files and directories should adhere to the established pattern above to maintain consistency.\n\n"

    content += "## Persistence Rules\n\n"
    content += "1. **Respect Boundaries**: Do not move files across functional boundaries (e.g., from `src/` to `tests/`) without justification.\n"
    content += "2. **No Reorganization**: Agents must work within this structure instead of imposing a new one unless explicitly requested.\n"
    content += "3. **Documentation**: Any significant structural changes must be updated in this `PROJECT.md` file.\n"

    return content


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."

    # Check if PROJECT.md already exists
    if os.path.exists(os.path.join(target, "PROJECT.md")):
        print("✅ PROJECT.md already exists. Workspace is currently guided.")
        sys.exit(0)

    print("🔍 Analyzing existing workspace structure...")
    structure, pattern = analyze_workspace(target)

    print(f"\nDetected dominant naming pattern: {pattern}")
    print("\nProposed PROJECT.md content:")
    print("-" * 30)
    print(generate_project_md(structure, pattern))
    print("-" * 30)
    print(
        "\nTo persist this structure, write the content above to 'PROJECT.md' at the root."
    )
