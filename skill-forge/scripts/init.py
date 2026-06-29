#!/usr/bin/env python3
"""Scaffold a new skill with constitution-compliant frontmatter.

Creates <name>/SKILL.md with the §5 frontmatter schema + the basic directory
structure (scripts/, references/, examples/, evals/).

Usage:
    python init.py <name>                           # defaults: auto/process
    python init.py grill --invocation user --layer process \
        --loop grill --deliverable "PRD.md + plan folder"
    python init.py use-clickup --layer domain --provides clickup-api
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

VALID_INVOCATIONS = {"auto", "user", "bootstrap"}
VALID_LAYERS = {"process", "domain", "utility"}


def generate_frontmatter(name: str, invocation: str, layer: str,
                          loop: str | None, deliverable: str | None,
                          provides: list[str]) -> str:
    fm = [
        "---",
        f"name: {name}",
        "description: |",
        "  What it does, briefly.",
        "  Use when [specific triggers].   # REQUIRED — 'Use when' literal MUST appear",
        f"invocation: {invocation}",
        f"layer: {layer}",
    ]
    if invocation == "user":
        fm.append(f"loop: {loop or '<loop-name>'}")
        fm.append(f"deliverable: {deliverable or '<named deliverable>'}")
    if layer == "domain":
        prov = ", ".join(provides) if provides else "<capability>"
        fm.append(f"provides: [{prov}]")
    fm += [
        "language: en-US",
        "metadata:",
        '  version: "1.0.0"',
        "---",
    ]
    return "\n".join(fm) + "\n"


SKILL_BODY = """
# {name}

## When (self-trigger)

- [Trigger 1 — symptom/context]
- [Trigger 2]

## What it does

[One paragraph. Express behavior, NEVER harness/tool names (§9 agnosticism).]

## References

- `references/` — deep docs loaded on demand
- `scripts/` — executable helpers
"""


def init_skill(name: str, target_dir: Path, invocation: str, layer: str,
               loop: str | None, deliverable: str | None,
               provides: list[str]) -> Path:
    import re
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        print(f"error: name '{name}' must be lowercase-hyphens", file=sys.stderr)
        sys.exit(1)
    if invocation not in VALID_INVOCATIONS:
        print(f"error: invocation must be {sorted(VALID_INVOCATIONS)}", file=sys.stderr)
        sys.exit(1)
    if layer not in VALID_LAYERS:
        print(f"error: layer must be {sorted(VALID_LAYERS)}", file=sys.stderr)
        sys.exit(1)

    skill_dir = target_dir / name
    if skill_dir.exists():
        print(f"error: {skill_dir} already exists", file=sys.stderr)
        sys.exit(1)
    skill_dir.mkdir(parents=True)
    for sub in ("scripts", "references", "examples", "evals"):
        (skill_dir / sub).mkdir()

    fm = generate_frontmatter(name, invocation, layer, loop, deliverable, provides)
    body = SKILL_BODY.format(name=name)
    (skill_dir / "SKILL.md").write_text(fm + body, encoding="utf-8")

    print(f"PASS created {skill_dir}/SKILL.md")
    print(f"     invocation={invocation} layer={layer}")
    if invocation == "user":
        print(f"     loop={loop or '<unset>'} deliverable={deliverable or '<unset>'}")
    if layer == "domain":
        print(f"     provides={provides or ['<unset>']}")
    print(f"     next: edit description to add real 'Use when' triggers")
    print(f"     verify: python skill-forge/scripts/audit.py {name}")
    return skill_dir


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold a constitution-compliant skill.")
    ap.add_argument("name", help="skill name (lowercase-hyphens)")
    ap.add_argument("--path", default=".", help="destination dir (default: cwd)")
    ap.add_argument("--invocation", default="auto", choices=sorted(VALID_INVOCATIONS))
    ap.add_argument("--layer", default="process", choices=sorted(VALID_LAYERS))
    ap.add_argument("--loop", help="loop name (required if --invocation user)")
    ap.add_argument("--deliverable", help="named deliverable (required if --invocation user)")
    ap.add_argument("--provides", nargs="*", default=[], help="capabilities (layer=domain)")
    args = ap.parse_args()

    if args.invocation == "user" and (not args.loop or not args.deliverable):
        print("error: --invocation user requires --loop and --deliverable", file=sys.stderr)
        return 1

    init_skill(args.name, Path(args.path).resolve(),
               args.invocation, args.layer, args.loop, args.deliverable, args.provides)
    return 0


if __name__ == "__main__":
    sys.exit(main())
