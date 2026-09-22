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
# Raw answers (no decision applied):
python jev_cli.py classify \
  --state "the slide says: 2+2 = 5" \
  --question score_at_max="noul:Did this slide achieve its maximum possible score?"

# Decision applied with the backend's threshold (exit 0=pass, 1=fail, 3=uncertain):
python jev_cli.py decide --state "..." --preset slide_done_v1
```

`classify` returns `{"answers": {...}, "mode": "...", "cost_usd": ..., "latency_ms": ...}`.
`decide` adds `{"decision": "pass"|"fail"|"uncertain", "confident", "threshold", "reasons"}`.

**Prefer `decide` in guardrails.** It resolves the threshold from the backend
that actually served the call.

## The decision contract

| Verdict | Meaning | Caller must |
|---|---|---|
| `pass` | The state satisfies the preset's rule | May act |
| `fail` | It does not | Retry, flag, or surface to a human |
| `uncertain` | **No signal** (fallback, error, no threshold) | Keep the existing heuristic |

`uncertain` is never a pass. It is the channel that lets this layer be added to a
working flow without changing its behaviour while credentials are missing.

### Thresholds belong to the BACKEND

The same answers score differently per backend. Measured on one H5P state:

| Backend | `score_at_max` | Scale |
|---|---|---|
| JEV (claimed) | ~0.99 | assertive |
| Laya (measured) | 0.81 | conservative |
| OpenRouter (LLM) | ~0.9 | uncalibrated |

A single fixed threshold across backends produces systematic false negatives.
`jev.json → thresholds_by_backend` resolves them per backend, and `decide`
applies the right one automatically. Override per call with `--threshold`.

## Backend policy — how Laya actually gets used

Having Laya installed is not the same as Laya being *chosen*. `decide` resolves the
backend from `jev.json → backend_policy`, which is an **ordered preference list per
preset**. It probes each entry and uses the first one actually available:

```json
"backend_policy": {
  "default":          ["laya", "openrouter", "vercel", "typesafe", "fallback"],
  "slide_done_v1":    ["laya", "openrouter", "fallback"],
  "ai_dimensions_v1": ["openrouter", "vercel", "typesafe", "fallback"]
}
```

- **Available** means: a key is present, or (for Laya) `GET /health` answers.
- **`ai_dimensions_v1` deliberately excludes Laya** — measured, it inverts that task.
- The chosen path ships in the output as `backend_trace`, so *"Laya was preferred
  but wasn't running"* is visible instead of silent.

```bash
# Sin --backend, manda la política del preset:
python jev_cli.py decide --state "..." --preset slide_done_v1
# -> {"mode": "openrouter", "backend_trace": [{"backend":"laya","available":false}, ...],
#     "backend_warning": "laya_preferida_pero_no_corria — se usó openrouter"}

# Arrancar Laya si la política la prefiere y no responde (nunca implícito:
# levanta un proceso de ~3.7 GB):
python jev_cli.py decide --state "..." --preset slide_done_v1 --auto-laya
JEV_AUTO_LAYA=1 python jev_cli.py decide ...   # equivalente por env
```

**So the guarantee is policy, not memory.** The preset decides the preference order;
the resolver picks the first available; the trace makes the fallback auditable. If
you want Laya to actually run for a batch, either start it once
(`python jev_cli.py laya up`) or pass `--auto-laya`.

## Laya on-demand (the no-egress lane)

Laya is a library, not a server. Two scripts turn it into an ephemeral service
for latency-sensitive loops:

```bash
# Start, run, kill. No daemon, no persistence, no egress.
python jev_cli.py laya up                              # start + print env
python jev_cli.py laya status
python jev_cli.py laya down
```

See `references/laya-on-demand.md`. Measured: 23-27s cold start, 25-76ms per
decision, 1.5 GB on disk, 0 bytes at rest, $0 per call.

## Schemas (presets)

`scripts/jev_schemas.py` ships with:

| Preset | Use case | Question types |
|---|---|---|
| `slide_done_v1` | H5P slide "did this score max?" | 2 Noul → `pass`/`fail` |
| `find_words_drag_v1` | FindTheWords drag safety | 3 Noul → `pass`/`fail` |
| `course_closed_v1` | Course completion check | 3 Noul + 1 Score → `pass`/`fail` |
| `render_gate_v1` | Video render quality | 1 Choice + 2 Noul → `pass`/`fail` |
| `ai_dimensions_v1` | AI-tell multi-dimension | 6 Noul + 1 Score + 1 Choice → score |
| `triage_quality_v1` | Research output triage | 1 Choice + 2 Noul + 1 Score → `pass`/`fail` |

`ai_dimensions_v1` has no binary rule (it is a composite score, not a gate);
`decide` returns `uncertain` for it by design. Use `classify` + your own weighting.

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
├── jev.json                  ← config (endpoints, pricing, thresholds_by_backend)
├── scripts/
│   ├── jev_client.py         ← Python API (4 backends + fallback)
│   ├── jev_schemas.py        ← presets + decision rules
│   ├── jev_cli.py            ← subprocess entry (classify | decide | laya)
│   ├── laya_server.py        ← HTTP wrapper so Laya looks like a JEV endpoint
│   ├── laya_on_demand.py     ← start → run → kill (the ephemeral pattern)
│   ├── render_gate.py        ← Scenario 4 helper
│   └── triage_quality.py     ← Scenario 6 helper
├── references/
│   ├── cost-log.jsonl        ← auto-created on first call
│   ├── recipes.md            ← usage per scenario
│   ├── comparison.md         ← backend decision aid (measured numbers)
│   └── laya-on-demand.md     ← the no-egress lane, end to end
└── tests/
    ├── test_jev_client.py
    ├── test_jev_schemas.py
    ├── test_jev_cli.py
    └── test_jev_decide.py    ← locks down the per-backend threshold bug
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
