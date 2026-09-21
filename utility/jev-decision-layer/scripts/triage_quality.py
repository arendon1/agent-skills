"""
triage_quality.py — Scenario 6 (research output triage).

After delegating research to a third-party LLM (agy/Gemini, web_search, etc.),
this script classifies the output and decides whether to follow up or move on.
Replaces the implicit "let me read this and decide" that's currently paid for
in m3 tokens (~800 tokens per triage event).

Cascade policy:
    if answer_addresses_question < 0.6 OR needs_followup == "yes_urgent":
        → trigger follow-up query
    elif needs_followup == "yes_nice":
        → log as nice-to-follow but proceed
    else:
        → proceed with this output

Usage:
    python triage_quality.py --input research_output.txt
    python triage_quality.py --input -  # stdin
    python triage_quality.py --input answer.md --question "What's the open-source alternative to JEV?"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

try:
    from jev_client import JEV  # type: ignore[import-not-found]
    from jev_schemas import TRIAGE_QUALITY_V1  # type: ignore[import-not-found]
except Exception as e:
    JEV = None  # type: ignore[assignment]
    TRIAGE_QUALITY_V1 = None  # type: ignore[assignment]
    _IMPORT_ERROR = e


# --------------------------------------------------------------------------- #
# Decision policy
# --------------------------------------------------------------------------- #
def apply_policy(verdict: dict, original_question: str | None = None) -> dict:
    answers = verdict.get("answers", {})

    if verdict.get("mode") == "fallback" or verdict.get("uncertain"):
        return {"action": "proceed_with_caution",
                "reason": "no_decision_layer",
                "hint": "consider reading the output yourself"}

    addresses = answers.get("answer_addresses_question", {}).get("value", 0.0)
    sources = answers.get("sources_are_cited", {}).get("value", 0.0)
    confidence = answers.get("confidence_in_finding", {}).get("value", 3)
    needs = answers.get("needs_followup", {}).get("value", "no")

    if needs == "yes_urgent" or addresses < 0.6:
        return {
            "action": "trigger_followup",
            "reason": f"addresses={addresses:.2f}_needs={needs}",
            "gap": {
                "addresses_question": addresses,
                "confidence": confidence,
                "sources_cited": sources,
            },
            "follow_up_prompt": (
                f"original_question: {original_question!r}\n"
                f"previous answers were weak (addresses={addresses:.2f}, "
                f"sources={sources:.2f}). "
                "Provide more concrete / cited information."
            ) if original_question else None,
        }

    if needs == "yes_nice":
        return {"action": "log_and_proceed",
                "reason": f"addresses={addresses:.2f}_sources={sources:.2f}",
                "log_level": "info"}

    return {"action": "proceed", "metrics": {
        "addresses_question": addresses, "sources_cited": sources,
        "confidence": confidence,
    }}


# --------------------------------------------------------------------------- #
# I/O
# --------------------------------------------------------------------------- #
def _read_input(args: argparse.Namespace) -> str:
    src = args.input or "-"
    if src == "-":
        return sys.stdin.read()
    return Path(src).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Triage a research-output text via JEV.")
    ap.add_argument("--input", help="Path to the research output ('-' for stdin).")
    ap.add_argument("--question", help="Original question (for follow-up prompt context).")
    ap.add_argument("--backend", choices=["auto", "vercel", "typesafe", "laya", "fallback"],
                    default="auto")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args()

    text = _read_input(args)
    if not text.strip():
        ap.error("provide --input (refusing to score empty output)")

    if JEV is None or TRIAGE_QUALITY_V1 is None:
        out = {"error": "jev-decision-layer not importable", "import_error": str(_IMPORT_ERROR)}
        print(json.dumps(out, indent=2 if args.pretty else None))
        return 3

    MAX_CHARS = 12_000
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[…truncated…]"

    backend = None if args.backend == "auto" else args.backend
    verdict = JEV(backend=backend).classify(text, TRIAGE_QUALITY_V1)
    policy = apply_policy(verdict.as_dict(), original_question=args.question)

    out = {
        "input_chars": len(text),
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
