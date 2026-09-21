---
name: jev-decision-layer
description: |
  Add a typed-decision classifier to any workflow that needs to gate, classify, route, or score
  **before** paying for an LLM judgment. Returns Choice/Score/Noul answers with probabilities.
  Four interchangeable backends: OpenRouter (default — already-authorized egress, JSON-schema
  constrained, ~1.6s, ~$0.00001/call), JEV via Vercel Gateway or TypeSafe direct (200-300ms,
  calibrated, new egress), and Laya (Apache 2.0, 421M, self-hosted, ~30ms). Degrades to a
  deterministic fallback when no credentials are set. Use when an agent makes a *binary or
  bounded* judgment about a state — slide done?, drag safe?, course closed?, render good?,
  AI-tell present?, research output acceptable? — when the same decision repeats many times
  per run, or when a heuristic gate is fragile and needs a probability behind it.
invocation: auto
layer: utility
provides: [decision-layer-classification, calibrated-probability-scoring, jev-client, laya-client]
language: en-US
---

# JEV Decision Layer

A small, leaf utility skill for **typed-decision classification** in agent
workflows. Wraps JEV (TypeSafe AI System One model) and presents it as a single
function with three question primitives:

- **Noul** — yes/no probability (0..1)
- **Choice** — pick 1 of N (≤255 options)
- **Score** — ordinal rating (1..N)

All outputs ship with calibrated probabilities so callers can pick thresholds
explicitly (no "trust the model" needed).

## When to use

Use when ANY of these hold:
- A bound decision (yes/no, pick-from-list, rate-1-to-5) is repeated many times.
- A heuristic gate is fragile and you'd like a calibrated probability behind it.
- Cost or latency of an LLM call for the same question is wasteful.
- You're about to ship a *gate* whose failure mode is silent corruption
  (e.g. "slide is done" check returning false positive).

## When NOT to use

- You need free-form generation, code, chat, or open-ended reasoning. Use the
  chat fleet for that — no System One model generates text.
- The decision space is open-ended (e.g. "describe what you see"). Out of scope.
- **The decision runs inside a tight per-item loop and latency is the point.**
  The OpenRouter route is ~1.6-2s; × 60 slides that is 2 minutes of added
  wall-clock. For those loops use Laya (30ms), JEV with an approved key
  (250ms), or skip the layer and keep the heuristic.
- The decision is irreversible and high-stakes. JEV's own accuracy benchmark is
  ~67.8% with no independent reproduction; the OpenRouter route has no
  calibration guarantee at all. Use as a guardrail, never as the final word.

## Access

| Route | Setup | Cost / call\* | Latency | Calibrated? | Egress |
|---|---|---|---|---|---|
| **OpenRouter** (default) | `OPENROUTER_API_KEY` — already configured fleet-wide | ~$0.00001 | ~1.6-2s | No | **Authorized (Tier 1)** |
| JEV via Vercel Gateway | `VERCEL_API_KEY` | ~$0.00002 | 200-300ms | Claimed, unverified | **New host — needs approval** |
| JEV via TypeSafe | `TYPESAFE_API_KEY` (waitlist) | ~$0.00002 | 200-300ms | Claimed, unverified | **New host — needs approval** |
| Laya (self-host) | `JEV_BACKEND=laya` + `JEV_BASE_URL=http://localhost:8000` | $0 (compute) | ~30-40ms | Yes (open) | None |
| Fallback (heuristic) | none — automatic | $0 | <1ms | No | None |

\*At our real state size (~200-500 tokens). JEV's advertised "40-400x cheaper" is measured
against **frontier** models (GPT-5.6 Sol at ~$0.084/case), not against our own cheap fleet.
Against `v4-text` at our state size the difference is ~$0.00001 per call.

**Auto-detection order**: local Laya > OpenRouter > Vercel > TypeSafe > fallback. The
authorized host wins over new egress, and a local server wins over both.

**Reasoning is off by default** on the OpenRouter route (`"reasoning": {"enabled": false}`).
Measured: 5.9s -> 1.6s, output tokens 108 -> 11. A classifier needs a bounded decision, not
a chain of thought. Set `JEV_OPENROUTER_REASONING=1` to re-enable (and pay the latency).

The client auto-detects: `JEV_BACKEND` env var wins; if unset, Vercel > TypeSafe
> Laya (in that order, by availability).

## Usage (Python)

```python
from jev_client import JEV

client = JEV()  # auto-detect backend from env
verdict = client.classify(
    state="The deploy failed twice and customers are seeing 500s. Can someone look now?",
    questions={
        "urgent": ("noul", "Does this need attention right now?"),
    },
)
# verdict["urgent"].value == 0.97 (calibrated probability)
# verdict.mode == "live" | "fallback" | "laya" | "vercel"
```

## Usage (subprocess — for cross-skill consumption, §12)

```bash
python jev_cli.py classify \
  --state "the slide says: 2+2 = 5" \
  --question score_at_max="noul:Did this slide achieve its maximum possible score?"
```

Returns JSON: `{"answers": {...}, "mode": "...", "cost_usd": 0.0001, "latency_ms": 230}`.

## Schemas (presets)

`scripts/jev_schemas.py` ships with:

| Preset | Use case | Question types |
|---|---|---|
| `slide_done_v1` | H5P slide "did this score max?" | 2 Noul |
| `find_words_drag_v1` | FindTheWords drag safety | 3 Noul |
| `course_closed_v1` | Course completion check | 3 Noul + 1 Score |
| `render_gate_v1` | Video render quality | 1 Choice + 2 Noul |
| `ai_dimensions_v1` | AI-tell multi-dimension | 6 Noul + 1 Score + 1 Choice |
| `triage_quality_v1` | Research output triage | 1 Choice + 2 Noul + 1 Score |

## Cost & ledger

Every call appends to `references/cost-log.jsonl` (auto-created on first call),
one JSON line per call:

```json
{"ts": "...", "mode": "live|fallback|...|laya|vercel", "preset": "slide_done_v1",
 "tokens_in": 540, "cost_usd": 0.000023, "latency_ms": 234, "questions": 2}
```

This lets us audit real spend monthly without re-querying the provider.

## Fallback semantics

When no API key is set, every call returns `mode: "fallback"` with a
heuristic-style answer drawn from the call's `state` and question text (deterministic).
This keeps existing flows running while we wait for credentials. The fallback is
**explicitly labeled** so callers know it's a stub.

To force fallback-off (so a missing key raises instead), set `JEV_STRICT=1`.

## Files

```
utility/jev-decision-layer/
├── SKILL.md                  ← this file
├── jev.json                  ← client config (mirror openrouter.json pattern)
├── scripts/
│   ├── jev_client.py         ← Python API
│   ├── jev_schemas.py        ← preset question templates
│   └── jev_cli.py            ← subprocess entry (for §12 cross-skill)
├── references/
│   ├── cost-log.jsonl        ← auto-created on first call
│   ├── recipes.md            ← usage recipes per scenario
│   └── comparison.md         ← JEV vs Laya vs fallback (decision aid)
└── tests/
    ├── test_jev_client.py
    ├── test_jev_schemas.py
    └── test_jev_cli.py
```

## Integration notes

- **Cross-skill consumption (§12)**: other skills call this utility through
  `subprocess` (via `jev_cli.py`), NEVER via code import. Their SKILL.md files
  should mention this utility by name as a "companion skill" hint.
- **Agnosticism (§9)**: this skill makes no reference to any specific harness,
  tool, model, or framework. The JEV/Laya references are part of the public
  product names, not harness bindings.
- **Audit**: `python utility/skill-forge/scripts/audit.py jev-decision-layer`
  must pass before merge.
