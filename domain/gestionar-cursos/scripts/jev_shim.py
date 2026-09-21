"""
JEV shim for the `gestionar-cursos` skill.

This is the §12-compliant bridge between `gestionar-cursos` (domain skill) and
the `jev-decision-layer` (utility skill). It:

  * invokes `jev_cli.py` as a subprocess (NEVER imports from that skill)
  * locates the CLI either via $JEV_SKILL_DIR or by walking up from this file
    to discover the sibling skill in the same repo
  * exposes a typed-result API: `classify()` returns a dataclass-shaped dict
    with explicit `mode` so callers can branch on fallback vs live
  * all failures degrade to `mode="fallback"` / `uncertain=True` — never raises

Usage from h5p_solve.py:

    from jev_shim import jev_slide_done, jev_drag_safe

    guard = jev_slide_done(state_blob)
    if not guard.confident_done:
        m["opportunities"].append("jev_guardarrail_low_confidence")
        # either retry or surface to human — never silently mark done
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Path discovery
# --------------------------------------------------------------------------- #
_HERE = Path(__file__).resolve().parent


def _locate_jev_cli() -> Path | None:
    """Find jev_cli.py in the jev-decision-layer utility skill.

    Priority order:
      1. $JEV_DECISION_LAYER_DIR env var (explicit override, useful in tests)
      2. A sibling skill at <repo-root>/utility/jev-decision-layer/scripts/jev_cli.py
         (auto-discovered by walking up from this file).
    """
    env = os.environ.get("JEV_DECISION_LAYER_DIR")
    if env:
        p = Path(env) / "scripts" / "jev_cli.py"
        return p if p.is_file() else None

    # Walk up: this file is at <repo>/domain/gestionar-cursos/scripts/jev_shim.py
    # We want <repo>/utility/jev-decision-layer/scripts/jev_cli.py
    cur = _HERE
    for _ in range(6):
        sibling = cur.parent.parent / "utility" / "jev-decision-layer" / "scripts" / "jev_cli.py"
        if sibling.is_file():
            return sibling
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


_CLI_PATH: Path | None = _locate_jev_cli()


# --------------------------------------------------------------------------- #
# Result types
# --------------------------------------------------------------------------- #
@dataclass
class GuardVerdict:
    """Result of a JEV classification, with explicit uncertainty channel.

    `confident_done` is the only field most callers need. The split between
    `mode`, `uncertain`, and `error_reason` lets you audit which path served.
    """

    confident: bool = False
    confident_done: bool = False  # sugar for `confident and verdict predicts done`
    mode: str = "fallback"        # live | vercel | laya | fallback | error
    cost_usd: float = 0.0
    latency_ms: int = 0
    raw: dict | None = None
    answers: dict[str, Any] = field(default_factory=dict)
    uncertain: bool = True        # True when we have no useful signal (fallback or error)
    error_reason: str | None = None
    preset: str | None = None


# --------------------------------------------------------------------------- #
# Core call
# --------------------------------------------------------------------------- #
def _run_cli(state: str, preset: str, backend: str | None = None,
             timeout: float = 8.0) -> GuardVerdict:
    """Invoke jev_cli.py as a subprocess and parse the JSON verdict."""
    if _CLI_PATH is None:
        return GuardVerdict(
            mode="fallback",
            uncertain=True,
            error_reason="jev-decision-layer not found (set JEV_DECISION_LAYER_DIR)",
            preset=preset,
        )

    args = [sys.executable, str(_CLI_PATH), "classify",
            "--state", state, "--preset", preset]
    if backend:
        args.extend(["--backend", backend])

    t0 = time.time()
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        latency = int((time.time() - t0) * 1000)
        if proc.returncode != 0:
            return GuardVerdict(
                mode="error",
                uncertain=True,
                error_reason=f"cli exit {proc.returncode}: {proc.stderr.strip()[:200]}",
                preset=preset,
                latency_ms=latency,
            )
        try:
            verdict = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            return GuardVerdict(
                mode="error",
                uncertain=True,
                error_reason=f"non-json output: {e}",
                preset=preset,
                latency_ms=latency,
            )
    except subprocess.TimeoutExpired:
        return GuardVerdict(
            mode="error",
            uncertain=True,
            error_reason=f"timeout ({timeout}s)",
            preset=preset,
            latency_ms=int(timeout * 1000),
        )
    except Exception as e:  # noqa: BLE001 — last-resort guard
        return GuardVerdict(
            mode="error",
            uncertain=True,
            error_reason=f"{type(e).__name__}: {str(e)[:200]}",
            preset=preset,
        )

    return GuardVerdict(
        mode=verdict.get("mode", "fallback"),
        uncertain=verdict.get("mode") in (None, "fallback", "error"),
        answers=verdict.get("answers", {}),
        cost_usd=verdict.get("cost_usd", 0.0),
        latency_ms=verdict.get("latency_ms", latency),
        raw=verdict,
        preset=preset,
        error_reason=verdict.get("error"),
    )


# --------------------------------------------------------------------------- #
# Public recipes
# --------------------------------------------------------------------------- #
def jev_slide_done(state_blob: str, *, threshold: float = 0.95,
                   backend: str | None = None) -> GuardVerdict:
    """Classify whether an H5P slide has achieved its maximum score.

    Returns a GuardVerdict whose `confident_done` is True only when BOTH
    `score_at_max` and `all_answers_committed` clear `threshold`.

    When the JEV backend is unavailable (fallback or error), `confident_done`
    is False and `uncertain=True`. Callers MUST honour the contract:
    if `uncertain`, treat the verdict as "don't auto-mark done".
    """
    v = _run_cli(state_blob, "slide_done_v1", backend=backend)
    if v.uncertain:
        return v  # the caller decides what to do with no signal

    sa = v.answers.get("score_at_max", {}).get("value", 0.0)
    aa = v.answers.get("all_answers_committed", {}).get("value", 0.0)
    v.confident = (sa >= threshold) and (aa >= threshold)
    v.confident_done = v.confident
    return v


def jev_drag_safe(canvas_geometry: dict, *, threshold: float = 0.95,
                  backend: str | None = None) -> GuardVerdict:
    """Classify whether a FindTheWords drag will reliably hit the canvas.

    Expects a small dict with viewports, word coords, and canvas rect — anything
    JSON-serializable works. Returns a verdict whose `confident` is True only when
    START/END fall in viewport AND the path is uninterrupted.

    When uncertain: NEVER emit the drag — fall back to the existing heuristic
    in `_drag_ftw`.
    """
    state = json.dumps(canvas_geometry, separators=(",", ":"), ensure_ascii=False)
    v = _run_cli(state, "find_words_drag_v1", backend=backend)
    if v.uncertain:
        return v

    start = v.answers.get("start_in_viewport", {}).get("value", 0.0)
    end = v.answers.get("end_in_viewport", {}).get("value", 0.0)
    path = v.answers.get("path_uninterrupted", {}).get("value", 0.0)
    v.confident = (start >= threshold) and (end >= threshold) and (path >= 0.90)
    v.confident_done = v.confident  # sugar; "done" here means "drag will land"
    return v


# --------------------------------------------------------------------------- #
# Diagnostics
# --------------------------------------------------------------------------- #
def cli_path() -> Path | None:
    """Public accessor for tests / diagnostics."""
    return _CLI_PATH


def is_available() -> bool:
    """Whether the JEV CLI was found at all. Useful for `--no-jev` flags."""
    return _CLI_PATH is not None
