import os
import sys
import shutil
from pathlib import Path

# Files that are allowed to stay in the root
SAFE_ROOT_FILES = {
    "README.md",
    "README",
    "LICENSE",
    "LICENSE.md",
    "COPYING",
    ".gitignore",
    "PROJECT.md",
    "CLAUDE.md",
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "requirements.txt",
    "uv.lock",
    "docker-compose.yml",
    "Dockerfile",
    "Makefile",
    "CMakeLists.txt",
    "next.config.js",
    "vite.config.ts",
    "tsconfig.json",
    "vercel.json",
    "SKILL.md",
    "metadata.json",
    "CHANGELOG.md",
    "AUTHENTICATION.md",
}

# Common ignore patterns
COMMON_IGNORE_PATTERNS = [
    # OS
    ".DS_Store",
    "Thumbs.db",
    # IDEs
    ".vscode/",
    ".idea/",
    "*.swp",
    "*.swo",
    # Python
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".env",
    ".venv/",
    "env/",
    "venv/",
    # Node
    "node_modules/",
    "npm-debug.log*",
    "yarn-debug.log*",
    "yarn-error.log*",
    # Build
    "dist/",
    "build/",
    "out/",
    # Workspace Manager
    ".review/",
]


def cleanup_workspace(target_dir):
    target = Path(target_dir).resolve()
    review_dir = target / ".review"
    gitignore_path = target / ".gitignore"

    print(f"🧹 Cleaning up workspace at: {target}")

    # 1. Update .gitignore
    print("🔍 Checking .gitignore...")
    existing_patterns = set()
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            existing_patterns = {
                line.strip() for line in f if line.strip() and not line.startswith("#")
            }

    missing_patterns = [p for p in COMMON_IGNORE_PATTERNS if p not in existing_patterns]

    if missing_patterns:
        with open(gitignore_path, "a") as f:
            f.write("\n# Added by workspace-manager\n")
            for p in missing_patterns:
                f.write(f"{p}\n")
        print(f"  - Added {len(missing_patterns)} patterns to .gitignore")
    else:
        print("  - .gitignore is already up to date")

    # 2. Identify Orphans and Move to .review
    orphans = []
    for item in target.iterdir():
        if item.is_file():
            if item.name not in SAFE_ROOT_FILES and not item.name.startswith("."):
                orphans.append(item)

    if orphans:
        review_dir.mkdir(exist_ok=True)
        review_md_path = review_dir / "REVIEW.md"

        # Prepare content for REVIEW.md
        with open(review_md_path, "a" if review_md_path.exists() else "w") as f:
            if not review_md_path.exists() or os.path.getsize(review_md_path) == 0:
                f.write("# Workspace Review Folder\n\n")
                f.write(
                    "The following files were identified as 'orphans' (files in the root directory that may not belong there).\n"
                )
                f.write(
                    "Please audit these files and move them to their appropriate locations or delete them.\n\n"
                )
                f.write("| File | Date Moved | Explanation |\n")
                f.write("| :--- | :--- | :--- |\n")

            for orphan in orphans:
                try:
                    dest = review_dir / orphan.name
                    # If file already exists in review, append a suffix
                    if dest.exists():
                        count = 1
                        while (
                            review_dir / f"{orphan.stem}_{count}{orphan.suffix}"
                        ).exists():
                            count += 1
                        dest = review_dir / f"{orphan.stem}_{count}{orphan.suffix}"

                    shutil.move(orphan, dest)
                    f.write(
                        f"| `{dest.name}` | {Path(dest).stat().st_mtime} | Moved from root. Audit required. |\n"
                    )
                    print(f"  - Moved orphan to .review: {orphan.name}")
                except Exception as e:
                    print(f"  ! Failed to move {orphan.name}: {e}")

    else:
        print("  - No orphan files found in root.")

    print("\n✅ Cleanup completed successfully!")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    cleanup_workspace(target)
