#!/usr/bin/env python3
"""Offline smoke test for the make-a-map skill.

Exercises projection math, transform, and SVG rendering with synthetic data.
Does NOT contact the network. Useful as a fast CI gate before any live run.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "make_a_map.py"


def main() -> int:
    print(f"smoke: invoking {SCRIPT.name} --self-test")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--self-test"],
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print(f"FAIL self-test exit={proc.returncode}", file=sys.stderr)
        return 1

    # Confirm audit passes via skill-forge
    audit = subprocess.run(
        [sys.executable, "utility/skill-forge/scripts/audit.py", "make-a-map"],
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(audit.stdout)
    if audit.returncode != 0:
        print(f"FAIL audit exit={audit.returncode}", file=sys.stderr)
        sys.stderr.write(audit.stderr)
        return 1

    print("PASS smoke: self-test + audit")
    return 0


if __name__ == "__main__":
    sys.exit(main())