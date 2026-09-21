# PRD — jev-decision-layer integration

## Goal

Adopt the System One model pattern (JEV by TypeSafe AI, or Laya open-source) as a
decision layer across our skill system. **Do not** add a new model to the chat
fleet — instead, classify "is this state passable / not passable / borderline"
**before** paying for an LLM judgment on hard work.

## Why

Six concrete use cases identified:

| # | Workflow | Cost now | Cost with JEV | Wall-clock impact |
|---|---|---|---|---|
| 1 | `gestionar-cursos` H5P solver — "did this slide actually score max?" | heuristic fails ~30% of time | $0.0001/slide @ 250ms | bug class eliminated |
| 2 | `gestionar-cursos` FindTheWords — "will this drag hit the canvas?" | 4 polls × ~600ms = 2.4s/drag | 1 call @ 250ms | 41s/run → 15s/run |
| 3 | Course completion auto-check | 5 min human review/curso | $0.0005/curso @ 2s | 50 min/mes si escala |
| 4 | Video render quality gate | 30s human review × N variants | $0.001/render @ 500ms | 50 min/batch → 1 min |
| 5 | `ai-check` — multi-dimension AI-tell scoring | heuristic capped at regex-able tells | $0.002/doc @ 600ms | 100× volumen enabled |
| 6 | Research delegation output triage | m3 token-cost per triage | $0.0003/triage @ 200ms | -240M m3 tokens/mes |

## Non-goals

- Do NOT add JEV as a chat model to the main fleet (it does not generate text).
- Do NOT replace SUBS-FIRST tier routing — JEV adds 250ms latency per call, which
  cancels its cost benefit at that scale.
- Do NOT replace the panel adversarial Gemini-lens (agy, free) with JEV.
- Do NOT add per-call dependencies on closed APIs without a graceful-degradation
  path; if no API key is configured, every JEV touchpoint returns a deterministic
  heuristic fallback and logs `mode=fallback`.

## Acceptance criteria

1. New utility skill `utility/jev-decision-layer/` exists, has SKILL.md + jev_client.py +
   jev_schemas.py + jev_cli.py + tests/, and passes `skill-forge audit`.
2. JEV client supports the dual access route (TypeSafe direct + Vercel AI Gateway) and
   transparently routes to whichever has credentials present.
3. When no credentials are configured, client returns `mode: "fallback"` with deterministic
   heuristic answers (do NOT raise — gracefully degrade so existing flows keep working).
4. Laya (Apache 2.0, 421M params) local endpoint is documented and configurable as an
   open-source drop-in (no code changes required, just `JEV_BACKEND=laya` env var +
   base URL).
5. Touchpoints implemented: at minimum Scenarios 1-3 and 5 from the table above.
   Scenarios 4 and 6 are documented patterns (recipes) but not mandatory implementations
   if budget is tight.
6. Cost ledger appends to `references/cost-log.jsonl` for every call (regardless of
   mode) so we can audit real spend.
7. SKILL files reference this utility via prose (per §12, no code imports across skills).

## Risks

| Risk | Mitigation |
|---|---|
| Closed API + key leak | Use env var ONLY; never persist to disk; doc in SKILL.md |
| Vendor could shut down or reprice | Laya open-source path is documented; switch is one env var |
| Calibration not yet independently verified | POC + A/B vs heuristic before promoting to default |
| Per-call latency might dominate for trivial calls | The `fallback` mode is instant (heuristic) when no key is set |
| Price subsidized today, may change at GA exit | Self-host Laya is the ceiling; cap uses at 52.6M req/mes break-even |
