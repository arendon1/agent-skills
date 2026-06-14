#!/usr/bin/env python3
"""Output audit prompt for skill evaluation.

Usage:
    python audit.py <skill-path>

Outputs a structured text prompt that agents consume to run audit checks.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict

PROJECT_SKILL_DIRS = [
    ".agents/skills",
    ".agent/skills",
    ".github/skills",
    ".gemini/skills",
    ".kiro/skills",
]

REPO_SKILL_DIRS = ["skills"]

GLOBAL_SKILL_DIRS = [
    ("~/.agents/skills", "~/.agents/skills"),
    ("~/.gemini/antigravity/skills", "~/.gemini/antigravity/skills"),
    ("~/.copilot/skills", "~/.copilot/skills"),
    ("~/.kiro/skills", "~/.kiro/skills"),
]


def find_skill(skill_identifier: str) -> Path | None:
    if Path(skill_identifier).is_absolute():
        p = Path(skill_identifier)
        if (p / "SKILL.md").exists():
            return p
        if p.is_dir() and (p.parent / "SKILL.md").exists():
            return p.parent

    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if parent != cwd and (parent / ".git").exists():
            break
        for skill_dir in PROJECT_SKILL_DIRS:
            skill_path = parent / skill_dir / skill_identifier
            if (skill_path / "SKILL.md").exists():
                return skill_path
        for skill_dir in REPO_SKILL_DIRS:
            skill_path = parent / skill_dir / skill_identifier
            if (skill_path / "SKILL.md").exists():
                return skill_path
        direct_path = parent / skill_identifier
        if (direct_path / "SKILL.md").exists():
            return direct_path

    home = Path.home()
    for local_key, global_path in GLOBAL_SKILL_DIRS:
        skill_path = Path(global_path.replace("~", str(home))) / skill_identifier
        if (skill_path / "SKILL.md").exists():
            return skill_path
    return None


def parse_frontmatter(skill_md: Path) -> Dict[str, str]:
    content = skill_md.read_text(encoding="utf-8")
    lines = content.split('\n')
    frontmatter = {}
    in_fm = False
    fm_lines = []

    for line in lines:
        if line.strip() == '---':
            if not in_fm:
                in_fm = True
                continue
            else:
                break
        if in_fm:
            fm_lines.append(line)

    current_key = None
    block_content = []
    in_block = False
    block_markers = ['>-', '|-', '>|', '|>']

    for l in fm_lines:
        l_stripped = l.rstrip()

        if any(l_stripped.endswith(marker) for marker in block_markers):
            current_key = l_stripped.split(':')[0].strip()
            in_block = True
            block_content = []
            continue
        elif in_block:
            if l_stripped == '' or l[0] != ' ':
                in_block = False
                frontmatter[current_key] = '\n'.join(block_content).strip()
                block_content = []
            else:
                block_content.append(l_stripped)
                continue

        m = re.match(r'^(\w+):\s*(.*)', l)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip().split('#')[0].strip()
            frontmatter[key] = val

    if in_block and current_key:
        frontmatter[current_key] = '\n'.join(block_content).strip()

    return frontmatter


def get_skill_info(skill_path: Path) -> Dict:
    skill_md = skill_path / "SKILL.md"
    frontmatter = parse_frontmatter(skill_md)

    content = skill_md.read_text(encoding="utf-8")
    lines = content.split('\n')

    documented_scripts = set()
    for m in re.finditer(r'(?:scripts?|script)[\s:>]+[`"]?([\w-]+\.(?:py|sh|js|ts|rb|mjs))', content, re.IGNORECASE):
        documented_scripts.add(m.group(1).lower())
    for m in re.finditer(r'\|\s*`?([\w-]+\.(?:py|sh|js|ts|rb|mjs))\s*`?\s*\|', content):
        documented_scripts.add(m.group(1).lower())

    scripts_dir = skill_path / "scripts"
    actual_scripts = set()
    if scripts_dir.exists():
        actual_scripts = {f.name.lower() for f in scripts_dir.iterdir()
                         if f.is_file() and f.name != "__init__.py"}

    return {
        "name": frontmatter.get("name", skill_path.name),
        "description": frontmatter.get("description", ""),
        "language": frontmatter.get("language", ""),
        "line_count": len(lines),
        "documented_scripts": sorted(documented_scripts),
        "actual_scripts": sorted(actual_scripts),
        "has_scripts_dir": scripts_dir.exists(),
        "has_references_dir": (skill_path / "references").exists(),
    }


def generate_audit_prompt(skill_path: Path) -> str:
    info = get_skill_info(skill_path)

    lines = [
        "SKILLFORGE AUDIT PROMPT",
        "=======================",
        "",
        f"Skill: {info['name']}",
        f"Path: {skill_path}",
        "",
        "CHECKS TO RUN:",
        "",
        "[1] FILE COVERAGE",
        f"  Documented scripts: {', '.join(info['documented_scripts']) or 'none'}",
        f"  Actual scripts: {', '.join(info['actual_scripts']) or 'none'}",
        "  Task: Verify documented files exist. Flag orphaned scripts.",
        "",
        "[2] STRUCTURE",
        f"  Name: {info['name']}",
        f"  Has description: {'yes' if info['description'] else 'NO'}",
        f"  Language: {info['language'] or 'MISSING'}",
        f"  Line count: {info['line_count']}",
        "  Task: Verify frontmatter has name, description, language. Check line count <= 500.",
        "",
        "[3] DESCRIPTION FORMAT",
        "  Required: Description must contain 'Use when...' or 'Usa cuando...'",
        "  Task: Verify trigger phrase is present.",
        "",
        "[4] LANGUAGE CONSISTENCY",
        f"  Declared: {info['language'] or 'MISSING'}",
        "  Allowed: en or es-CO",
        "  Task: Verify all content matches declared language.",
        "",
        "[5] SECURITY SCAN",
        "  Dangerous patterns to find: os.system, shell=True, eval(), exec(), __import__(), base64.b64decode",
        "  Task: Scan scripts/ directory. Report any matches.",
        "",
        "[6] LENGTH",
        f"  Max lines: 500",
        f"  Current: {info['line_count']}",
        f"  Status: {'PASS' if info['line_count'] <= 500 else 'FAIL'}",
        "  Task: Verify SKILL.md is under 500 lines.",
        "",
        "INSTRUCTIONS:",
        "  1. Spawn subagents to run each check in parallel",
        "  2. Each subagent reports pass/fail with details",
        "  3. Aggregate results and report specific issues found",
        "",
        "OUTPUT FORMAT:",
        "  summary: passed=X failed=Y warnings=Z",
        "  issues:",
        "    - check=... severity=error|warning message=...",
        "",
    ]

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Output audit prompt for skill evaluation")
    parser.add_argument("skill", help="Skill name or absolute path")
    args = parser.parse_args()

    skill_path = find_skill(args.skill)
    if not skill_path:
        print(f"Error: Skill not found: {args.skill}", file=sys.stderr)
        sys.exit(1)

    prompt = generate_audit_prompt(skill_path)
    print(prompt)


if __name__ == "__main__":
    main()