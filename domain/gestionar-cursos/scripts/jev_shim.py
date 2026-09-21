"""
JEV shim for the `gestionar-cursos` skill.

§12-compliant bridge between `gestionar-cursos` (domain skill) and
`jev-decision-layer` (utility skill). It:

  * invokes `jev_cli.py` as a subprocess (NEVER imports from that skill)
  * locates the CLI via $JEV_DECISION_LAYER_DIR or by walking up the repo
  * calls the `decide` verb, so the BACKEND-AWARE threshold is applied by the
    CLI rather than hardcoded here. (Measured 2026-09-21: Laya scores 0.5546 on
    a state where JEV would say 0.99 — a shared fixed threshold produces
    systematic false negatives.)
  * never raises: every failure degrades to decision="uncertain"

Usage from h5p_solve.py:

    from jev_shim import jev_slide_done, jev_drag_safe

    guard = jev_slide_done(state_blob)
    if guard.decision == "pass":
        mark_done()
    elif guard.decision == "fail":
        retry_or_flag()
    else:                       # "uncertain" — no signal, fall back to heuristic
        keep_existing_logic()
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
    """Find jev_cli.py — explicit env override, else sibling-skill discovery."""
    env = os.environ.get("JEV_DECISION_LAYER_DIR")
    if env:
        p = Path(env) / "scripts" / "jev_cli.py"
        return p if p.is_file() else None

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

# Exit codes from `jev_cli.py decide` (documented contract)
_RC_TO_DECISION = {0: "pass", 1: "fail", 3: "uncertain"}


# --------------------------------------------------------------------------- #
# Result type
# --------------------------------------------------------------------------- #
@dataclass
class GuardVerdict:
    """Result of a decision-layer call.

    Contract for callers:
      * decision == "pass"  -> the state satisfies the preset's rule
      * decision == "fail"  -> it does not
      * decision == "uncertain" -> NO SIGNAL (fallback, error, no threshold).
                                   Callers MUST keep their existing heuristic.
    """

    decision: str = "uncertain"       # pass | fail | uncertain
    confident: bool = False           # decision == "pass"
    mode: str = "fallback"            # openrouter | vercel | typesafe | laya | fallback | error
    threshold: float | None = None
    reasons: list[str] = field(default_factory=list)
    answers: dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: int = 0
    preset: str | None = None
    error_reason: str | None = None
    raw: dict | None = None

    @property
    def confident_done(self) -> bool:
        """Back-compat alias for older callers: True only on an explicit pass."""
        return self.decision == "pass"

    @property
    def uncertain(self) -> bool:
        return self.decision == "uncertain"


# --------------------------------------------------------------------------- #
# Core call
# --------------------------------------------------------------------------- #
def _run_cli(state: str, preset: str, backend: str | None = None,
             timeout: float = 15.0, threshold: float | None = None) -> GuardVerdict:
    """Invoke `jev_cli.py decide` and parse the verdict. Never raises."""
    if _CLI_PATH is None:
        return GuardVerdict(
            decision="uncertain", mode="fallback", preset=preset,
            error_reason="jev-decision-layer not found (set JEV_DECISION_LAYER_DIR)",
        )

    args = [sys.executable, str(_CLI_PATH), "decide", "--state", state, "--preset", preset]
    if backend:
        args.extend(["--backend", backend])
    if threshold is not None:
        args.extend(["--threshold", str(threshold)])

    t0 = time.time()
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        latency = int((time.time() - t0) * 1000)
        decision = _RC_TO_DECISION.get(proc.returncode)
        if decision is None:
            return GuardVerdict(
                decision="uncertain", mode="error", preset=preset, latency_ms=latency,
                error_reason=f"cli exit {proc.returncode}: {(proc.stderr or '').strip()[:200]}",
            )
        try:
            v = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            return GuardVerdict(
                decision="uncertain", mode="error", preset=preset, latency_ms=latency,
                error_reason=f"non-json output: {e}",
            )
    except subprocess.TimeoutExpired:
        return GuardVerdict(
            decision="uncertain", mode="error", preset=preset,
            error_reason=f"timeout ({timeout}s)", latency_ms=int(timeout * 1000),
        )
    except Exception as e:  # noqa: BLE001 — last-resort guard
        return GuardVerdict(
            decision="uncertain", mode="error", preset=preset,
            error_reason=f"{type(e).__name__}: {str(e)[:200]}",
        )

    return GuardVerdict(
        decision=v.get("decision", decision),
        confident=bool(v.get("confident", decision == "pass")),
        mode=v.get("mode", "fallback"),
        threshold=v.get("threshold"),
        reasons=v.get("reasons") or [],
        answers=v.get("answers") or {},
        cost_usd=v.get("cost_usd", 0.0),
        latency_ms=v.get("latency_ms", latency),
        preset=preset,
        error_reason=v.get("error"),
        raw=v,
    )


# --------------------------------------------------------------------------- #
# Public recipes
# --------------------------------------------------------------------------- #
def jev_slide_done(state_blob: str, *, backend: str | None = None,
                   threshold: float | None = None) -> GuardVerdict:
    """Decide whether an H5P slide achieved its maximum score.

    The threshold is resolved by the CLI from `jev.json -> thresholds_by_backend`
    for whichever backend actually served the call.
    """
    return _run_cli(state_blob, "slide_done_v1", backend=backend, threshold=threshold)


def jev_drag_safe(canvas_geometry: dict, *, backend: str | None = None,
                  threshold: float | None = None) -> GuardVerdict:
    """Decide whether a FindTheWords drag will reliably hit the canvas."""
    state = json.dumps(canvas_geometry, separators=(",", ":"), ensure_ascii=False)
    return _run_cli(state, "find_words_drag_v1", backend=backend, threshold=threshold)


# --------------------------------------------------------------------------- #
# Diagnostics / on-demand helpers
# --------------------------------------------------------------------------- #
def cli_path() -> Path | None:
    return _CLI_PATH


def is_available() -> bool:
    return _CLI_PATH is not None


def active_backend() -> str:
    """Which backend the CLI would pick right now (no network call)."""
    if os.environ.get("JEV_BACKEND"):
        return os.environ["JEV_BACKEND"]
    if os.environ.get("JEV_BASE_URL", "").startswith("http://localhost") or \
       os.environ.get("JEV_BASE_URL", "").startswith("http://127.0.0.1"):
        return "laya"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.environ.get("VERCEL_API_KEY") or os.environ.get("AI_GATEWAY_API_KEY"):
        return "vercel"
    if os.environ.get("TYPESAFE_API_KEY"):
        return "typesafe"
    return "fallback"