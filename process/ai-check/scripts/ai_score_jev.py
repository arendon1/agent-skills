"""
ai_score_jev.py — JEV-powered re-arquitectura of the ai-check skill.

The base ai-check SKILL.md defines 9 signal categories scored 0-3 by an LLM
reading the document. This script substitutes the LLM call with a single JEV
call that scores ALL dimensions in parallel as typed questions, returning
calibrated probabilities per dimension.

Per Scenario 5 from the JEV integration plan:
  * Cost: ~$0.002 per document (12 questions × ~500 token input)
  * Latency: ~600ms end-to-end (vs LLM: 3-5s)
  * Confidence: a calibrated probability per dimension (LLM can't give this)
  * Composite score: weighted sum of the 6 Noul answers + composite Score
  * Mode-aware: returns mode="fallback" with deterministic scores when no key

The script is a thin wrapper — the heavy lifting happens in
`utility/jev-decision-layer/scripts/jev_client.py` and `jev_schemas.py`.

Usage:
    python ai_score_jev.py --file path/to/doc.txt
    python ai_score_jev.py --file doc.txt --json
    cat doc.txt | python ai_score_jev.py --stdin
    echo "free-form text..." | python ai_score_jev.py --stdin --pretty
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent.parent / "utility" / "jev-decision-layer" / "scripts"))

# The jev-decision-layer skill is the canonical owner of the client/schema.
# This script lives here ONLY because §12 forbids cross-skill code imports:
# we add its `scripts/` to sys.path and import as if it were a sibling.
try:
    from jev_client import JEV  # type: ignore[import-not-found]
    from jev_schemas import AI_DIMENSIONS_V1  # type: ignore[import-not-found]
except Exception as e:
    JEV = None  # type: ignore[assignment]
    AI_DIMENSIONS_V1 = None  # type: ignore[assignment]
    _IMPORT_ERROR = e


# --------------------------------------------------------------------------- #
# Composite scoring
# --------------------------------------------------------------------------- #
WEIGHTS: dict[str, float] = {
    "has_em_dash_overuse": 0.15,
    "uses_banned_vocab": 0.25,
    "uniform_sentence_len": 0.20,
    "templated_structure": 0.15,
    "voice_consistency": 0.10,
    "human_likelihood": 0.15,        # inverted in scoring
}

# Mapping choice answer ("highly_templated" / "somewhat_templated" / "natural") to 0..1
TEMPLATE_PROB = {"highly_templated": 0.9, "somewhat_templated": 0.5, "natural": 0.1}


def composite_score(answers: dict[str, Any]) -> dict[str, Any]:
    """Combine per-dimension answers into a 0-100 composite.

    Higher score = more likely AI-generated. Mirrors the same shape the
    LLM-based ai-check returns (a single number with confidence).
    """
    if not answers:
        return {"composite": None, "label": "no-answers", "components": {}}

    components: dict[str, float] = {}
    weighted_sum = 0.0
    weight_total = 0.0

    em = answers.get("has_em_dash_overuse", {}).get("value", 0.0)
    components["em_dash_overuse"] = em
    weighted_sum += em * WEIGHTS["has_em_dash_overuse"]
    weight_total += WEIGHTS["has_em_dash_overuse"]

    banned = answers.get("uses_banned_vocab", {}).get("value", 0.0)
    components["banned_vocab"] = banned
    weighted_sum += banned * WEIGHTS["uses_banned_vocab"]
    weight_total += WEIGHTS["uses_banned_vocab"]

    uniform = answers.get("uniform_sentence_len", {}).get("value", 0.0)
    components["uniform_sentence_len"] = uniform
    weighted_sum += uniform * WEIGHTS["uniform_sentence_len"]
    weight_total += WEIGHTS["uniform_sentence_len"]

    templ = answers.get("templated_structure", {}).get("value", "natural")
    templ_p = TEMPLATE_PROB.get(str(templ), 0.5)
    components["templated_structure"] = templ_p
    weighted_sum += templ_p * WEIGHTS["templated_structure"]
    weight_total += WEIGHTS["templated_structure"]

    voice_raw = answers.get("voice_consistency", {}).get("value", 3)
    # Voice consistency 1..5, where 1=jarring / 5=single voice. AI often has
    # overly-consistent voice; map to AI-likelihood.
    if isinstance(voice_raw, (int, float)):
        voice_ai = max(0.0, min(1.0, (voice_raw - 1) / 4.0))
    else:
        voice_ai = 0.5
    components["voice_consistency"] = voice_ai
    weighted_sum += voice_ai * WEIGHTS["voice_consistency"]
    weight_total += WEIGHTS["voice_consistency"]

    hum_raw = answers.get("human_likelihood", {}).get("value", 5)
    if isinstance(hum_raw, (int, float)):
        hum_ai = max(0.0, min(1.0, (10 - hum_raw) / 9.0))
    else:
        hum_ai = 0.5
    components["human_likelihood_inverted"] = hum_ai
    weighted_sum += hum_ai * WEIGHTS["human_likelihood"]
    weight_total += WEIGHTS["human_likelihood"]

    score_0_1 = weighted_sum / weight_total if weight_total > 0 else 0.0
    score_0_100 = round(score_0_1 * 100, 1)
    label = (
        "very_likely_human" if score_0_100 < 20
        else "likely_human" if score_0_100 < 40
        else "mixed_signals" if score_0_100 < 60
        else "likely_ai" if score_0_100 < 80
        else "very_likely_ai"
    )
    return {"composite": score_0_100, "label": label, "components": components,
            "weight_total": weight_total, "weighted_sum": round(weighted_sum, 4)}


# --------------------------------------------------------------------------- #
# I/O helpers
# --------------------------------------------------------------------------- #
def _read_input(args: argparse.Namespace) -> str:
    if args.stdin:
        return sys.stdin.read()
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    return ""


def _emit(obj: dict, pretty: bool) -> None:
    if pretty:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(obj, ensure_ascii=False))


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Score a document for AI-tell signals via JEV.")
    ap.add_argument("--file", help="Path to the document to score.")
    ap.add_argument("--stdin", action="store_true", help="Read the document from stdin.")
    ap.add_argument("--json", action="store_true", help="Emit JSON object (default).")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    ap.add_argument("--backend", choices=["auto", "openrouter", "vercel", "typesafe", "laya", "fallback"],
                    default="auto")
    args = ap.parse_args()

    text = _read_input(args)
    if not text.strip():
        ap.error("provide --file or --stdin (refusing to score empty input)")

    if JEV is None or AI_DIMENSIONS_V1 is None:
        out = {
            "error": "jev-decision-layer not importable from this path",
            "import_error": str(_IMPORT_ERROR),
            "mode": "import_error",
            "hint": "ensure utility/jev-decision-layer/scripts/ is on sys.path",
        }
        _emit(out, args.pretty)
        return 3

    # Truncate to a sane size for JEV's context budget
    MAX_CHARS = 20_000
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[…truncated for scoring…]"

    backend = None if args.backend == "auto" else args.backend
    client = JEV(backend=backend)
    verdict = client.classify(text, AI_DIMENSIONS_V1)

    composite = composite_score(verdict.as_dict()["answers"])

    out = {
        "document_chars": len(text),
        "decision_layer": {
            "mode": verdict.mode,
            "cost_usd": verdict.cost_usd,
            "latency_ms": verdict.latency_ms,
            "tokens_in": verdict.tokens_in,
            "request_id": verdict.request_id,
            "error": verdict.error,
        },
        "answers": verdict.as_dict()["answers"],
        "composite": composite,
    }
    _emit(out, args.pretty)
    return 0


if __name__ == "__main__":
    sys.exit(main())
