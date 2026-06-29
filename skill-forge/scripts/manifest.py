#!/usr/bin/env python3
"""Generate .claude-plugin/marketplace.json by scanning skills and grouping by layer.

The skills CLI (npx skills) reads .claude-plugin/marketplace.json and surfaces
skills grouped by plugin `name`. We map our architectural layers (process/domain/
utility) onto plugin groups, so the CLI's grouping matches the constitution §3.

The filesystem + frontmatter `layer:` field is the single source of truth
(AGENTS.md §2: never hardcode a skill list). This manifest is a GENERATED build
artifact — regenerate whenever skills are added/renamed/moved. `audit.py` flags a
stale manifest.

Usage:
    python manifest.py                 # write .claude-plugin/marketplace.json
    python manifest.py --check         # exit 1 if tracked manifest is stale
    python manifest.py --print         # print to stdout, don't write
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# reuse the audit frontmatter parser
sys.path.insert(0, str(Path(__file__).parent))
from audit import parse_frontmatter, find_skill  # noqa: E402

LAYER_ORDER = ["process", "domain", "utility"]
MANIFEST_PATH = Path(".claude-plugin/marketplace.json")


def discover_skills(root: Path) -> list[tuple[str, str]]:
    """Return [(name, layer)] for every subdir with a SKILL.md, sorted by name."""
    out: list[tuple[str, str]] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)
        name = str(fm.get("name", d.name)).strip()
        layer = str(fm.get("layer", "")).strip()
        out.append((name, layer))
    return out


def build_manifest(root: Path) -> dict:
    skills = discover_skills(root)
    by_layer: dict[str, list[str]] = {l: [] for l in LAYER_ORDER}
    unclassified: list[str] = []
    for name, layer in skills:
        if layer in by_layer:
            by_layer[layer].append(f"./{name}")
        else:
            unclassified.append(f"./{name}")
    plugins = [
        {"name": layer, "source": ".", "skills": by_layer[layer]}
        for layer in LAYER_ORDER if by_layer[layer]
    ]
    if unclassified:
        plugins.append({"name": "unclassified", "source": ".", "skills": unclassified})
    return {"metadata": {"pluginRoot": "."}, "plugins": plugins}


def manifest_str(m: dict) -> str:
    return json.dumps(m, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate .claude-plugin/marketplace.json by layer.")
    ap.add_argument("--check", action="store_true", help="exit 1 if tracked manifest is stale")
    ap.add_argument("--print", action="store_true", help="print manifest, don't write")
    args = ap.parse_args()

    root = Path.cwd()
    m = build_manifest(root)
    out = manifest_str(m)

    if args.print:
        sys.stdout.write(out)
        return 0

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if args.check:
        existing = MANIFEST_PATH.read_text(encoding="utf-8") if MANIFEST_PATH.exists() else ""
        if existing.strip() != out.strip():
            print(f"FAIL manifest stale: {MANIFEST_PATH}", file=sys.stderr)
            print("  regenerate with: python skill-forge/scripts/manifest.py", file=sys.stderr)
            return 1
        n = sum(len(p["skills"]) for p in m["plugins"])
        print(f"PASS manifest fresh ({n} skills, {len(m['plugins'])} groups)")
        return 0

    MANIFEST_PATH.write_text(out, encoding="utf-8")
    n = sum(len(p["skills"]) for p in m["plugins"])
    groups = ", ".join(f"{p['name']}={len(p['skills'])}" for p in m["plugins"])
    print(f"PASS wrote {MANIFEST_PATH} ({n} skills: {groups})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
