# ai-check ↔ jev-decision-layer integration

The canonical `ai-check` SKILL.md describes 9 signal categories scored 0-3 by an LLM
reading the document. The companion script `scripts/ai_score_jev.py` substitutes that
LLM call with a single batched JEV call that returns calibrated probabilities per
dimension in <600ms.

## When to use which

- **LLM-based ai-check (canonical SKILL.md)**: the human-facing service that produces
  a rich narrative report (citation per signal, prose diagnosis, suggested rewrites).
  Use when the user wants an explanation.
- **JEV ai-check (`scripts/ai_score_jev.py`)**: the high-volume scoring path. Use when:
  you need to score 100+ documents, you only need a score (not prose), or you want a
  confidence interval alongside the verdict.

## What ai_score_jev.py returns

```json
{
  "decision_layer": {
    "mode": "live" | "fallback" | "laya" | "vercel",
    "cost_usd": 0.002,
    "latency_ms": 540,
    "tokens_in": 1842,
    "request_id": "abc123",
    "error": null
  },
  "answers": {
    "has_em_dash_overuse": {"type": "noul", "value": 0.78, "probability": 0.78},
    "uses_banned_vocab":   {"type": "noul", "value": 0.62, "probability": 0.62},
    "uniform_sentence_len":{"type": "noul", "value": 0.71, "probability": 0.71},
    "templated_structure": {"type": "choice", "value": "highly_templated",
                            "probability": 0.74},
    "voice_consistency":   {"type": "score", "value": 5},
    "human_likelihood":    {"type": "score", "value": 3}
  },
  "composite": {
    "composite": 76.2,
    "label": "likely_ai",
    "components": { ... },
    "weight_total": 1.0,
    "weighted_sum": 0.762
  }
}
```

## Thresholds

| Composite | Label | Recommended action |
|---|---|---|
| 0-20 | very_likely_human | Publish without AI-warning |
| 20-40 | likely_human | Optional light rewrite |
| 40-60 | mixed_signals | Human review |
| 60-80 | likely_ai | Mandatory rewrite before publish |
| 80-100 | very_likely_ai | Block publish or rewrite from scratch |

## Setup

1. Install `utility/jev-decision-layer/` (this repo, sibling utility skill).
2. Set `VERCEL_AI_GATEWAY_API_KEY` (or `TYPESAFE_API_KEY`) in the environment.
3. `python scripts/ai_score_jev.py --file doc.txt` returns the verdict above.
4. Without a key, the script returns `mode="fallback"` with deterministic
   heuristics. Useful for tests; do NOT use it for production scoring.

## Cross-skill consumption (§12)

`ai_score_jev.py` lives in this skill's `scripts/` and calls the JEV client's
CLI as an HTTP fetch (same skill namespace, no §12 violation). Other skills that
want to score text via this path should shell-out: `python process/ai-check/scripts/ai_score_jev.py --file <path>`.
