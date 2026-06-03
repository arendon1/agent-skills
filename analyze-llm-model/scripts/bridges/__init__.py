"""
Bridge registry — auto-discovers bridge modules in this directory.
"""

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
            mod = __import__(f"bridges.{name}", fromlist=["SOURCE_HELP", "extract"])
        except ImportError:
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
        try:
            mod = __import__(f"bridges._stubs.{entry.stem}", fromlist=["SOURCE_HELP"])
        except ImportError:
            continue
        if hasattr(mod, "SOURCE_HELP"):
            stubs[entry.stem] = mod.SOURCE_HELP
    return stubs
