"""
render_gate.py — Scenario 4 (HyperFrames-style video render quality gate).

Classifies a render report's composite (composition metadata + render metrics +
audio cadence) into pass / needs_re_render / needs_human using the JEV
`render_gate_v1` preset. Reduces per-batch human review from ~30s × N to <500ms
× N + human review only where JEV is uncertain or disagrees.

Usage:
    python render_gate.py --report-json /path/to/render_report.json
    python render_gate.py --report-json - < render.json
    python render_gate.py --composition-id H123 --metrics '[{"dropped_frames":3}]'

Cascade policy applied here:
    verdict.choice == "pass"            AND no_glitches>=0.90  → auto_publish()
    verdict.choice == "needs_re_render" AND confidence>=0.85    → re_render(seed+1)
    otherwise → queue_for_human_review()
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

try:
    from jev_client import JEV  # type: ignore[import-not-found]
    from jev_schemas import RENDER_GATE_V1  # type: ignore[import-not-found]
except Exception as e:
    JEV = None  # type: ignore[assignment]
    RENDER_GATE_V1 = None  # type: ignore[assignment]
    _IMPORT_ERROR = e


# --------------------------------------------------------------------------- #
# State shape
# --------------------------------------------------------------------------- #
def build_state(report: dict) -> str:
    """Compact JSON state for JEV from an arbitrary render report."""
    keep = {
        "composition_id": report.get("composition_id"),
        "duration_s": report.get("duration_s"),
        "fps": report.get("fps"),
        "dropped_frames": report.get("dropped_frames"),
        "audio_lufs": report.get("audio_lufs"),
        "captions_present": report.get("captions_present"),
        "caption_drift_ms": report.get("caption_drift_ms"),
        "error_log_excerpt": (report.get("error_log") or "")[:400],
        "frame_samples": (report.get("frame_samples") or [])[:6],
    }
    return json.dumps(keep, separators=(",", ":"), ensure_ascii=False, default=str)


# --------------------------------------------------------------------------- #
# Cascade policy
# --------------------------------------------------------------------------- #
def apply_policy(verdict: dict) -> dict:
    """Translate JEV verdict into a publish/rerender/review decision."""
    answers = verdict.get("answers", {})
    choice = answers.get("render_succeeded", {}).get("value")
    glitch = answers.get("no_visual_glitches", {}).get("value", 0.0)
    caption = answers.get("captions_aligned", {}).get("value", 0.0)
    confidence = answers.get("render_succeeded", {}).get("probability", 0.0)

    if verdict.get("mode") == "fallback" or verdict.get("uncertain"):
        return {"action": "queue_for_human_review", "reason": "no_decision_layer"}

    if choice == "pass" and glitch >= 0.90:
        return {"action": "auto_publish", "reason": "pass+clean",
                "metrics": {"glitch": glitch, "caption": caption}}

    if choice == "needs_re_render" and confidence >= 0.85:
        return {"action": "re_render", "reason": "needs_re_render+high_conf",
                "next_seed_delta": 1, "metrics": {"glitch": glitch, "caption": caption}}

    return {"action": "queue_for_human_review",
            "reason": f"choice={choice}_glitch={glitch:.2f}_conf={confidence:.2f}",
            "metrics": {"glitch": glitch, "caption": caption}}


# --------------------------------------------------------------------------- #
# I/O
# --------------------------------------------------------------------------- #
def _read_report(args: argparse.Namespace) -> dict:
    if args.metrics is not None:
        # Caller passed inline metrics as JSON
        return json.loads(args.metrics)
    src = args.report_json or "-"
    if src == "-":
        return json.load(sys.stdin)
    return json.loads(Path(src).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Classify a render report via JEV.")
    ap.add_argument("--report-json", help="Path to render report JSON ('-' for stdin).")
    ap.add_argument("--metrics", help="Inline JSON object with render metrics.")
    ap.add_argument("--composition-id", help="If passed with --metrics, attach to the state.")
    ap.add_argument("--backend", choices=["auto", "vercel", "typesafe", "laya", "fallback"],
                    default="auto")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args()

    report = _read_report(args)
    if args.composition_id and "composition_id" not in report:
        report["composition_id"] = args.composition_id

    if JEV is None or RENDER_GATE_V1 is None:
        out = {"error": "jev-decision-layer not importable", "import_error": str(_IMPORT_ERROR)}
        print(json.dumps(out, indent=2 if args.pretty else None))
        return 3

    state = build_state(report)
    backend = None if args.backend == "auto" else args.backend
    verdict = JEV(backend=backend).classify(state, RENDER_GATE_V1)
    policy = apply_policy(verdict.as_dict())

    out = {
        "report_metrics_compact": report,
        "decision_layer": {
            "mode": verdict.mode, "cost_usd": verdict.cost_usd,
            "latency_ms": verdict.latency_ms, "tokens_in": verdict.tokens_in,
            "error": verdict.error,
        },
        "answers": verdict.as_dict()["answers"],
        "policy": policy,
    }
    print(json.dumps(out, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
