import os
import sys
import re
from pathlib import Path


def validate_skill(skill_path: Path) -> bool:
    """
    Validates the skill according to structural standards:
    - SKILL.md exists and is under 500 lines
    - Frontmatter contains description starting with "Use when..."
    - References are maximum 1 depth deep
    """
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        print("❌ Error: missing SKILL.md")
        return False

    with open(skill_md, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) > 500:
        print(
            f"❌ Error: SKILL.md is {len(lines)} lines long. Maximum is 500. Extract details to references/ instead."
        )
        return False

    description_found = False
    use_when_found = False

    in_frontmatter = False
    for i, line in enumerate(lines):
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue

        if in_frontmatter:
            if line.startswith("description:"):
                description_found = True
            if "Use when" in line or "use when" in line:
                use_when_found = True

        if i > 50 and not in_frontmatter:  # Abort parsing if we're past the head
            break

    if not description_found:
        print("❌ Error: Missing 'description' in SKILL.md frontmatter")
        return False

    if not use_when_found:
        print("❌ Error: Description must explicitly state 'Use when [triggers]'.")
        return False

    # Check depth of references
    ref_dir = skill_path / "references"
    if ref_dir.exists():
        for root, dirs, files in os.walk(ref_dir):
            depth = Path(root).relative_to(ref_dir).parts
            if len(depth) > 0:
                print(
                    f"❌ Error: Nested directory found in references/ ({root}). References must be 1 level deep maximum."
                )
                return False

    return True


def security_scan(skill_path: Path) -> bool:
    """
    Performs a basic static analysis on scripts/ to look for malicious patterns.
    """
    scripts_dir = skill_path / "scripts"
    if not scripts_dir.exists():
        return True  # Nothing to scan

    bad_patterns = [
        r"os\.system",
        r"subprocess\.Popen\(shell=True\)",
        r"\beval\(",
        r"\bexec\(",
        r"__import__",
        r"base64\.b64decode",
    ]

    passed = True
    for root, dirs, files in os.walk(scripts_dir):
        for file in files:
            if not file.endswith(".py") and not file.endswith(".sh"):
                continue

            # Skip self-linting for validate_and_audit.py's own string assertions
            if file == "validate_and_audit.py":
                continue

            filepath = Path(root) / file
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    for pattern in bad_patterns:
                        if re.search(pattern, content):
                            print(
                                f"⚠️ Security Warning: Suspicious pattern '{pattern}' found in {filepath.name}"
                            )
                            passed = False
            except Exception as e:
                print(f"Error reading {filepath.name} for security scan: {e}")

    if not passed:
        print("❌ Security scan failed. Please audit the script files.")

    return passed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("Validate a skill")
    parser.add_argument("skill_dir", help="Path to the skill directory")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    print(f"Auditing {skill_dir.name}...")

    if validate_skill(skill_dir) and security_scan(skill_dir):
        print(f"✅ Success! {skill_dir.name} passed all validation and security checks.")
    else:
        sys.exit(1)
