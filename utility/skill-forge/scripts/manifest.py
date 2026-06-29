#!/usr/bin/env python3
"""Generate .claude-plugin/marketplace.json by scanning skills and grouping by layer.

The skills CLI (npx skills) reads .claude-plugin/marketplace.json and surfaces
skills grouped by plugin `name`. We map our architectural layers (process/domain/
utility) onto plugin groups, so the CLI's grouping matches the constitution §3.

Manifest format note (Format A):
  - OMIT `metadata.pluginRoot` and each plugin's `source`. The skills CLI's
    `isValidRelativePath()` is `path.startsWith("./")`, so `pluginRoot: "."`
    is INVALID and silently skips the entire plugins loop (no discovery, no
    grouping). Each `skills` entry MUST be a full "./..." relative path.
  - This is verified to make both the manifest-dir walk AND grouping work.

The filesystem + frontmatter `layer:` field is the single source of truth
(AGENTS.md §2). This manifest is a GENERATED build artifact — regenerate
whenever skills are added/renamed/moved. `audit.py` flags a stale manifest.

Layout: skills live in category buckets — `<layer>/<skill>/` at the repo root
(AGENTS.md §2). This scanner recurses one level into each known layer bucket.

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
from audit import parse_frontmatter  # noqa: E402

LAYER_ORDER = ["process", "domain", "utility"]
MANIFEST_PATH = Path(".claude-plugin/marketplace.json")


def discover_skills(root: Path) -> list[tuple[str, str]]:
    """Return [(name, layer)] for every SKILL.md, scanning category buckets.

    Skills live in `<layer>/<skill>/` buckets at the repo root (AGENTS.md §2).
    Scan each known layer bucket's immediate children. Also fall back to a
    root-level scan for any skill not yet moved into a bucket (covers the
    pre-reorganization state and any stragglers).
    """
    out: list[tuple[str, str]] = []
    seen_dirs: set[Path] = set()

    # 1. bucket scan: <layer>/<skill>/SKILL.md
    for layer in LAYER_ORDER:
        bucket = root / layer
        if not bucket.is_dir():
            continue
        for d in sorted(bucket.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            skill_md = d / "SKILL.md"
            if not skill_md.exists():
                continue
            seen_dirs.add(d.resolve())
            fm, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            name = str(fm.get("name", d.name)).strip()
            declared_layer = str(fm.get("layer", "")).strip()
            # trust the frontmatter layer; fall back to the bucket if absent
            eff_layer = declared_layer if declared_layer in LAYER_ORDER else layer
            out.append((name, eff_layer))

    # 2. root-level fallback: any <skill>/SKILL.md directly at repo root
    #    (skills not yet bucketed). Path entry is "./<name>".
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in LAYER_ORDER:
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists() or d.resolve() in seen_dirs:
            continue
        fm, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        name = str(fm.get("name", d.name)).strip()
        layer = str(fm.get("layer", "")).strip()
        if layer not in LAYER_ORDER:
            layer = "process"
        out.append((name, layer))

    return out


def build_manifest(root: Path) -> dict:
    skills = discover_skills(root)
    by_layer: dict[str, list[str]] = {l: [] for l in LAYER_ORDER}
    unclassified: list[str] = []

    for name, layer in skills:
        # path reflects the bucket layout: <layer>/<name>
        if name and layer in by_layer:
            # check whether the skill is actually in a bucket vs root
            bucket_path = root / layer / name
            root_path = root / name
            if bucket_path.exists():
                by_layer[layer].append(f"./{layer}/{name}")
            elif root_path.exists():
                by_layer[layer].append(f"./{name}")
            else:
                by_layer[layer].append(f"./{layer}/{name}")
        else:
            unclassified.append(f"./{name}")

    # de-dup + sort
    for l in by_layer:
        by_layer[l] = sorted(set(by_layer[l]))

    plugins = [
        {"name": layer, "skills": by_layer[layer]}
        for layer in LAYER_ORDER if by_layer[layer]
    ]
    if unclassified:
        plugins.append(
            {"name": "unclassified", "skills": sorted(set(unclassified))}
        )
    # Format A: NO metadata.pluginRoot, NO plugin.source. Full "./..." paths only.
    return {"plugins": plugins}


def manifest_str(m: dict) -> str:
    return json.dumps(m, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate .claude-plugin/marketplace.json by layer (Format A)."
    )
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if tracked manifest is stale")
    ap.add_argument("--print", action="store_true",
                    help="print manifest, don't write")
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
            print("  regenerate with: python skill-forge/scripts/manifest.py",
                  file=sys.stderr)
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
