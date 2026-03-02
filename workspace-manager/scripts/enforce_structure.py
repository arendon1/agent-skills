import os
import sys


def check_structure(root_dir):
    issues = []

    # Standard required files/folders for a healthy repo
    required_paths = ["docs", "README.md", ".gitignore"]

    # Check for presence of required items
    for path in required_paths:
        full_path = os.path.join(root_dir, path)
        if not os.path.exists(full_path):
            issues.append(f"MISSING: Recommended path '{path}' not found.")

    # Check for naming convention (kebab-case or snake_case)
    for root, dirs, files in os.walk(root_dir):
        # Skip hidden directories like .git, .agent
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for name in dirs + files:
            if " " in name:
                issues.append(
                    f"CONVENTION: '{name}' contains spaces. Use kebab-case or snake_case."
                )
            if (
                any(c.isupper() for c in name)
                and not name.endswith(".md")
                and name != "README.md"
                and name != "LICENSE"
            ):
                # Relaxed for common uppercase files
                if name not in [
                    "Dockerfile",
                    "Makefile",
                    "CMakeLists.txt",
                    "PROJECT.md",
                    "CLAUDE.md",
                ]:
                    issues.append(
                        f"CONVENTION: '{name}' contains uppercase letters. Prefer lowercase for internal files."
                    )

    return issues


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    issues = check_structure(target)

    if not issues:
        print("✅ Directory structure follows standards.")
    else:
        print("❌ Organization issues found:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
