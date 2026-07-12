#!/usr/bin/env python3
"""Direct constitution enforcer for agent-skills.

Validates a skill against AGENTS.md (the constitution). Exit 0 = PASS, 1 = FAIL.
Replaces the old prompt-output audit. Checks §5 frontmatter, §4 triggering,
§3 layers, §9 agnosticism, §15 constraints.

Usage:
    python audit.py <skill-name-or-path>
    python audit.py <skill-name> --strict     # warnings -> failures
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Frontmatter parser (no pyyaml dependency)
# ---------------------------------------------------------------------------

BLOCK_SCALAR_MARKERS = ("|", ">", "|-", ">-", "|+", ">+", "|-", "|>")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body). Body = everything after the closing ---."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1 :])
    fm: dict[str, Any] = {}
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        m = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).rstrip()
        # block scalar
        if rest in BLOCK_SCALAR_MARKERS or rest == "":
            if rest in BLOCK_SCALAR_MARKERS:
                block: list[str] = []
                i += 1
                while i < len(fm_lines) and (fm_lines[i].startswith("  ") or fm_lines[i].startswith("\t")):
                    block.append(fm_lines[i].strip())
                    i += 1
                fm[key] = " ".join(block).strip() if rest.startswith(">") else "\n".join(block).strip()
                continue
            # empty -> could be nested map or list
            if i + 1 < len(fm_lines) and re.match(r"^\s+-\s", fm_lines[i + 1]):
                items: list[str] = []
                i += 1
                while i < len(fm_lines) and re.match(r"^\s+-\s", fm_lines[i]):
                    items.append(re.sub(r"^\s+-\s+", "", fm_lines[i]).strip().strip('"').strip("'"))
                    i += 1
                fm[key] = items
                continue
            # nested map (e.g. metadata:) — capture presence, skip children
            i += 1
            while i < len(fm_lines) and (fm_lines[i].startswith("  ") or fm_lines[i].startswith("\t")):
                i += 1
            fm[key] = True
            continue
        # inline list
        if rest.startswith("[") and rest.endswith("]"):
            fm[key] = [x.strip().strip('"').strip("'") for x in rest[1:-1].split(",") if x.strip()]
            i += 1
            continue
        # scalar
        fm[key] = rest.strip('"').strip("'").split("#")[0].strip()
        i += 1
    return fm, body


# ---------------------------------------------------------------------------
# Skill discovery
# ---------------------------------------------------------------------------

def find_skill(identifier: str) -> Path | None:
    p = Path(identifier)
    if p.is_absolute() or "/" in identifier:
        if (p / "SKILL.md").exists():
            return p
        if p.is_file() and p.name == "SKILL.md":
            return p.parent
        if p.is_dir() and (p.parent / "SKILL.md").exists():
            return p.parent
    cwd = Path.cwd()
    # Skills live in category buckets: <layer>/<skill>/ (AGENTS.md §2).
    # Search the layer buckets first, then the repo root, then ancestors.
    candidates = []
    for layer in ("process", "domain", "utility"):
        candidates.append(cwd / layer / identifier)
    candidates.append(cwd / identifier)
    candidates.append(cwd / "skills" / identifier)  # legacy Matt-style layout
    for parent in cwd.parents:
        for layer in ("process", "domain", "utility"):
            candidates.append(parent / layer / identifier)
        candidates.append(parent / identifier)
    for c in candidates:
        if (c / "SKILL.md").exists():
            return c
    return None


# ---------------------------------------------------------------------------
# Agnosticism checks (§9)
# ---------------------------------------------------------------------------

# Whole-word harness names. \bpi\b avoids matching "api", "copy", "pip", "typing".
HARNESS_NAMES = [
    (r"\bpi\b", "pi"),
    (r"Claude Code", "Claude Code"),
    (r"OpenCode", "OpenCode"),
    (r"\bCursor\b", "Cursor"),
    (r"Antigravity", "Antigravity"),
    (r"\bCopilot\b", "Copilot"),
    (r"\bKiro\b", "Kiro"),
]
# Unambiguous tool-API names (capitalized or snake-case tool calls).
TOOL_APIS = [r"TodoWrite", r"soul_recall", r"\bsoul_recall\b"]
# Slash-command syntax in body: /word or /word:word. Require 2+ chars and exclude
# relative paths (./x, ../x) and HTML closing tags (</word>).
SLASH_CMD = re.compile(r"(?<![A-Za-z0-9/_.<])/(?!docs/|opt/|usr/|tmp/|var/|etc/|home/|dev/|proc/|sys/)[a-z][a-z0-9-]{1,}(?::[a-z0-9-]+)?(?![A-Za-z0-9/_])")


def strip_code(text: str) -> str:
    """Remove fenced code blocks and inline code so heuristic scans don't flag
    API paths, HTML tags, or commands that live inside code."""
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"~~~[\s\S]*?~~~", "", text)
    text = re.sub(r"`[^`]*`", "", text)
    return text


def agnosticism_violations(body: str) -> list[tuple[str, str, str]]:
    """Return [(severity, pattern_name, matched_text), ...]. severity = FAIL or WARN."""
    out: list[tuple[str, str, str]] = []
    # Scan prose only (no code) for both harness names and tool APIs — those
    # identifiers legitimately appear inside bash/python blocks as values.
    prose = strip_code(body)
    for pat, label in HARNESS_NAMES:
        for m in re.finditer(pat, prose):
            out.append(("FAIL", f"harness name '{label}'", m.group(0)))
    for pat in TOOL_APIS:
        for m in re.finditer(pat, prose):
            out.append(("FAIL", f"tool API '{pat}'", m.group(0)))
    # slash-command syntax: warn (already in prose)
    for m in SLASH_CMD.finditer(prose):
        token = m.group(0)
        # skip obvious URLs/paths
        ctx = prose[max(0, m.start() - 2) : m.end() + 2]
        if "://" in ctx or token.startswith("//"):
            continue
        out.append(("WARN", "slash-command syntax (use prose 'run the X loop')", token))
    return out


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


VALID_INVOCATIONS = {"auto", "user", "bootstrap"}
VALID_LAYERS = {"process", "domain", "utility"}
VALID_LANGS = {"en-US", "es-CO"}
MAX_LINES = 500


def audit(skill_path: Path) -> Result:
    r = Result()
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        r.errors.append(f"no SKILL.md at {skill_md}")
        return r
    text = skill_md.read_text(encoding="utf-8")
    lines = text.split("\n")
    fm, body = parse_frontmatter(text)

    # --- frontmatter present
    if not fm:
        r.errors.append("frontmatter missing (no --- block)")

    # --- name
    name = str(fm.get("name", "")).strip()
    if not name:
        r.errors.append("frontmatter: 'name' missing")
    else:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            r.errors.append(f"name '{name}' not lowercase-hyphens")
        if name != skill_path.name:
            r.errors.append(f"name '{name}' != directory name '{skill_path.name}'")

    # --- description + Use when
    desc = str(fm.get("description", "")).strip()
    if not desc:
        r.errors.append("frontmatter: 'description' missing")
    elif "use when" not in desc.lower() and "usa cuando" not in desc.lower():
        r.errors.append("description missing 'Use when' (or 'Usa cuando') trigger phrase")

    # --- invocation
    inv = str(fm.get("invocation", "")).strip()
    if not inv:
        r.errors.append("frontmatter: 'invocation' missing")
    elif inv not in VALID_INVOCATIONS:
        r.errors.append(f"invocation '{inv}' not in {sorted(VALID_INVOCATIONS)}")

    # --- layer
    layer = str(fm.get("layer", "")).strip()
    if not layer:
        r.errors.append("frontmatter: 'layer' missing")
    elif layer not in VALID_LAYERS:
        r.errors.append(f"layer '{layer}' not in {sorted(VALID_LAYERS)}")

    # --- user-invoked loop + deliverable (§4 enforceable rule)
    if inv == "user":
        if not str(fm.get("loop", "")).strip():
            r.errors.append("invocation=user but 'loop' missing")
        if not str(fm.get("deliverable", "")).strip():
            r.errors.append("invocation=user but 'deliverable' missing")

    # --- bootstrap uniqueness (only the bootstrap skill)
    if inv == "bootstrap" and name and name != "bootstrap":
        r.errors.append(f"invocation=bootstrap reserved for the 'bootstrap' skill, not '{name}'")

    # --- domain provides (§5 — warning if missing)
    if layer == "domain":
        prov = fm.get("provides")
        if not prov or (isinstance(prov, list) and not [x for x in prov if x]):
            r.warnings.append("layer=domain but 'provides' missing/empty (lists capabilities)")

    # --- language
    lang = str(fm.get("language", "")).strip()
    if lang and lang not in VALID_LANGS:
        r.warnings.append(f"language '{lang}' not in {sorted(VALID_LANGS)} (omit if unsure)")

    # --- size (§15)
    n = len(lines)
    if n > MAX_LINES:
        r.errors.append(f"SKILL.md is {n} lines, max {MAX_LINES}")
    else:
        r.infos.append(f"SKILL.md {n} lines (<= {MAX_LINES})")

    # --- agnosticism (§9) — body only, not frontmatter
    for sev, label, matched in agnosticism_violations(body):
        msg = f"§9 agnosticism: {label} (matched '{matched}')"
        if sev == "FAIL":
            r.errors.append(msg)
        else:
            r.warnings.append(msg)

    return r


def report(name: str, skill_path: Path, r: Result, strict: bool) -> int:
    print(f"skill-forge audit: {name}")
    print(f"  path: {skill_path}")
    for e in r.errors:
        print(f"  FAIL   {e}")
    for w in r.warnings:
        print(f"  WARN   {w}")
    for i in r.infos:
        print(f"  INFO   {i}")
    if r.errors:
        print(f"  -> FAIL ({len(r.errors)} error(s), {len(r.warnings)} warning(s))")
        return 1
    if r.warnings and strict:
        print(f"  -> FAIL (--strict: {len(r.warnings)} warning(s) treated as errors)")
        return 1
    verdict = "PASS" if not r.warnings else "PASS (with warnings)"
    print(f"  -> {verdict}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Direct constitution enforcer for agent-skills.")
    ap.add_argument("skill", help="skill name or path (e.g. caveman or ./caveman)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    skill_path = find_skill(args.skill)
    if not skill_path:
        print(f"error: skill not found: {args.skill}", file=sys.stderr)
        return 2
    name = skill_path.name
    r = audit(skill_path)
    return report(name, skill_path, r, args.strict)


if __name__ == "__main__":
    sys.exit(main())
