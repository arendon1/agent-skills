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
    language_field = None

    in_frontmatter = False
    frontmatter_text = ""
    body_text = ""

    for i, line in enumerate(lines):
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue

        if in_frontmatter:
            frontmatter_text += line
            if line.startswith("description:"):
                description_found = True
            if "Use when" in line or "use when" in line or "Usa cuando" in line:
                use_when_found = True
            if "language:" in line:
                language_field = (
                    line.split("language:")[1].strip().split("#")[0].strip()
                )
        else:
            body_text += line

        if i > 100 and not in_frontmatter and len(body_text) > 1000:
            # We have enough to check consistency later
            pass

    if not description_found:
        print("❌ Error: Missing 'description' in SKILL.md frontmatter")
        return False

    if not use_when_found:
        print("❌ Error: Description must explicitly state 'Use when [triggers]'.")
        return False

    if not language_field:
        print(
            "❌ Error: Missing 'language' in metadata frontmatter (e.g., language: en or language: es-CO)"
        )
        return False

    if language_field not in ["en", "es-CO"]:
        print(
            f"❌ Error: Unsupported language '{language_field}'. Supported: en, es-CO"
        )
        return False

    # Language Consistency Heuristic
    en_markers = {"the", "and", "for", "with", "when", "using", "from", "should"}
    es_markers = {
        "el",
        "la",
        "los",
        "las",
        "para",
        "con",
        "cuando",
        "usando",
        "desde",
        "debe",
    }

    words = set(re.findall(r"\b\w+\b", body_text.lower()))
    en_count = len(words.intersection(en_markers))
    es_count = len(words.intersection(es_markers))

    if language_field == "en" and es_count > en_count and es_count > 2:
        print(
            f"⚠️ Warning: Skill marked as 'en' but seems to contain significant Spanish content."
        )
    elif language_field == "es-CO" and en_count > es_count and en_count > 2:
        print(
            f"⚠️ Warning: Skill marked as 'es-CO' but seems to contain significant English content."
        )

    # Check depth of references
    ref_dir = skill_path / "references"
    if ref_dir.exists():
        for root, dirs, files in os.walk(ref_dir):
            try:
                depth = Path(root).relative_to(ref_dir).parts
                if len(depth) > 0:
                    print(
                        f"❌ Error: Nested directory found in references/ ({root}). References must be 1 level deep maximum."
                    )
                    return False
            except ValueError:
                continue

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
        print(
            f"✅ Success! {skill_dir.name} passed all validation and security checks."
        )
    else:
        sys.exit(1)
