"""
Bridge registry — auto-discovers bridge modules in this directory.
"""

import importlib
from pathlib import Path
from typing import Any

_BRIDGES_DIR = Path(__file__).parent
_EXCLUDE = {"__init__.py", "base.py"}


def discover_bridges() -> dict[str, Any]:
    """
    Scan bridges/ for modules with SOURCE_HELP and extract().
    Excludes _stubs/ and non-Python files.
    Returns {name: module} dict.
    """
    bridges: dict[str, Any] = {}
    for entry in _BRIDGES_DIR.iterdir():
        if entry.is_dir():
            continue
        if entry.suffix != ".py" or entry.name in _EXCLUDE:
            continue

        name = entry.stem
        try:
            mod = importlib.import_module(f".{name}", package=__package__)
        except ImportError as e:
            import sys
            print(f"Warning: Failed to import bridge '{name}': {e}", file=sys.stderr)
            continue

        if hasattr(mod, "SOURCE_HELP") and hasattr(mod, "extract"):
            bridges[name] = mod

    return bridges


def discover_stubs() -> dict[str, str]:
    """
    Scan bridges/_stubs/ for stubbed bridges.
    Returns {name: SOURCE_HELP} dict (help text only, no extract()).
    """
    stubs_dir = _BRIDGES_DIR / "_stubs"
    if not stubs_dir.is_dir():
        return {}

    stubs: dict[str, str] = {}
    for entry in stubs_dir.iterdir():
        if entry.suffix != ".py":
            continue
        if entry.name == "__init__.py":
            continue
        try:
            mod = importlib.import_module(f"._stubs.{entry.stem}", package=__package__)
        except ImportError as e:
            import sys
            print(f"Warning: Failed to import stub '{entry.stem}': {e}", file=sys.stderr)
            continue
        if hasattr(mod, "SOURCE_HELP"):
            stubs[entry.stem] = mod.SOURCE_HELP
    return stubs
