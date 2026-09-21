# Backend comparison — decision aid

Measured on 2026-09-21 against a real H5P-slide state (~250 tokens).

## The honest table

| | OpenRouter (v4-text) | JEV (Vercel/TypeSafe) | Laya (self-host) | Fallback |
|---|---|---|---|---|
| **Egress host** | `openrouter.ai` — **already authorized (Tier 1)** | `ai-gateway.vercel.sh` / `api.typesafe.ai` — **new, needs approval** | none (localhost) | none |
| **Cost / call** | **$0.0000136** (measured) | ~$0.00002 | $0 (compute) | $0 |
| **Latency** | 2011ms (measured, reasoning off) | 200-300ms (claimed, real-world) | ~30-40ms (claimed) | <1ms |
| **Calibrated probabilities** | **No** — heuristic 0..1 | Claimed (RLCD); **no independent verification** | Yes (open weights) | No |
| **Schema guarantee** | Yes (`response_format: json_schema`, strict) | Yes (by construction) | Yes | No |
| **Vendor** | Existing (already paying) | New (TypeSafe) | None (Apache 2.0) | None |
| **Setup** | Already configured | Get key + authorize host | `pip install laya` + GPU | none |

## The "100-400x cheaper" claim, decoded

TypeSafe's headline compares JEV against **frontier** models:

| Model | Cost / case (10K-token state) |
|---|---|
| GPT-5.6 Sol | $0.0836 |
| Opus 5 | ~$0.0574 |
| **JEV** | **$0.0004** |
| **v4-text (ours)** | **$0.000655** |

Against *our own cheap fleet* — the only comparison that matters for our spend —
JEV is **1.6× cheaper**, not 400×. And at our real state size (~500 tokens, not 10K),
the absolute difference is **$0.00001 per call**: at 10K calls/month, **18 cents**.

## The latency serialization problem

The OpenRouter route is an LLM constrained to a schema. Left to reason, it spends
most of the budget thinking:

| Strategy | Latency | Output tokens |
|---|---|---|
| default | 5.9s | 108 |
| **reasoning off** | **1.6s** | **11** |
| effort low | 7.7s | 160 |

`reasoning: {"enabled": false}` is therefore the default. Even so, ~1.6s is
**6-8× slower than JEV**. That gap is the entire remaining argument for a
System One model.

## Decision guidance

```
Is the decision inside a tight per-item loop?
├── Yes (60 slides, 9 words) → latency dominates
│   └── Laya (30ms) > JEV w/ approved key (250ms) > skip the layer
└── No (one course check, one doc score, one triage)
    └── OpenRouter — authorized, ~2s, $0.00001. Use it.
```

## Per-scenario recommendation

| Scenario | Loop? | Backend | Why |
|---|---|---|---|
| 1. H5P slide guardarraíl | **yes** (×60) | skip, or Laya | 1.6s × 60 = +96s |
| 2. FindTheWords drag check | **yes** (×9) | skip, or Laya | 1.6s × 9 = +14s |
| 3. Course close check | no (×1) | **OpenRouter** | 2s total, negligible cost |
| 4. Render gate | no (×N variants) | **OpenRouter** | 2s × 10 = 20s, still beats 5 min of human review |
| 5. ai-check scoring | no (×1 per doc) | **OpenRouter** | ~2s/doc, enables 100× volume |
| 6. Research triage | no (×1 per call) | **OpenRouter** | ~2s vs an m3 read |

## What is genuinely lost by choosing OpenRouter

1. **Calibration.** A constrained LLM emits a plausible number, not a calibrated
   probability. Do not threshold on it as if it were one. If a workflow needs
   "act when confidence > 0.95", that workflow needs JEV or Laya.
2. **Determinism.** LangChain measured JEV's per-case variance at 433× lower than
   an LLM judge. Two runs on the same state can disagree on the OpenRouter route.
3. **Sub-second latency.**

## When to revisit

- If the POC (RESEARCH.md §8) shows JEV's calibration genuinely holds → JEV/Laya
  earns the latency-sensitive loops.
- If Laya proves out locally → no egress, no vendor, 30ms. Strictly better for
  the tight loops.
- Until then: OpenRouter is the default, and it costs less than the spreadsheet
  row it is printed on.