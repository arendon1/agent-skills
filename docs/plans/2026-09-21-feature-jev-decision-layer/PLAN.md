# PLAN — jev-decision-layer integration

## Tasks

| ID | Status | Task | Files | Notes |
|---|---|---|---|---|
| T.1 | [x] | Create utility skill skeleton | `utility/jev-decision-layer/{SKILL.md,scripts,references,tests}/` | §5 frontmatter schema |
| T.2 | [x] | jev_client.py — dual-backend (TypeSafe + Vercel Gateway + Laya) + fallback | `utility/jev-decision-layer/scripts/jev_client.py` | Mock mode if no key |
| T.3 | [x] | jev_schemas.py — 6 preset templates | `utility/jev-decision-layer/scripts/jev_schemas.py` | slide_done, drag_safe, course_closed, render_quality, ai_dimensions, triage_quality |
| T.4 | [x] | jev_cli.py (subprocess entry §12) | `utility/jev-decision-layer/scripts/jev_cli.py` | JSON in/out |
| T.5 | [x] | jev.json config | `utility/jev-decision-layer/jev.json` | profiles per scenario |
| T.6 | [x] | Unit tests — 52 passing | `utility/jev-decision-layer/tests/test_jev_*.py` | pytest |
| T.7 | [x] | Scenario 1+2: H5P guardarraíl + drag-check | `domain/gestionar-cursos/scripts/h5p_solve.py` + `jev_shim.py` | Subprocess to jev_cli |
| T.8 | [x] | Scenario 3: verificar_cierre_curso.py | `domain/gestionar-cursos/scripts/verificar_cierre_curso.py` | New file |
| T.9 | [x] | Scenario 4: render gate helper + recipe | `utility/jev-decision-layer/scripts/render_gate.py` | Cascade policy |
| T.10 | [x] | Scenario 5: ai-check integration | `process/ai-check/` + `scripts/ai_score_jev.py` | SKILL trimmed to 499 lines |
| T.11 | [x] | Scenario 6: triage helper | `utility/jev-decision-layer/scripts/triage_quality.py` | |
| T.12 | [x] | Update CONTEXT.md glossary | `CONTEXT.md` | decision layer, guardarraíl, jev-shim |
| T.13 | [x] | Cost ledger + first audit | `references/cost-log.jsonl` (auto) | log header verified |
| T.14 | [x] | Conventional commits | (commits) | One commit per skill |
| T.15 | [x] | Planner → Reviewer pipeline (JEV-as-Pi-tool) | `references/plan-*.md`, `references/review-*.md` | CONDITIONAL-GO with 1 critical + 4 major fixes |
| T.16 | [x] | LESSONS.md | `LESSONS.md` | 8 lessons |
| T.17 | [x] | Verify: skill-forge audit PASS | shell | jev-decision-layer PASS, ai-check PASS |

## Status legend

`[ ]` pending · `[x]` done · `[~]` in progress · `[!]` blocked · `[-]` cancelled

## Bloqueado / pendiente de decisión humana

- **API key**: no configurada. Todo corre en `mode="fallback"`. Para pasar a `live`,
  setear `VERCEL_AI_GATEWAY_API_KEY` (ruta sin waitlist) o `TYPESAFE_API_KEY`.
- **Nuevos hosts de egreso** (`ai-gateway.vercel.sh`, `api.typesafe.ai`): requieren
  announce-then-run y autorización explícita (Reviewer C1). **No se ha llamado a ninguno.**
- **Wire-format del Gateway**: incógnita declarada. Verificar antes de activar la tool
  de Pi (`references/plan-jev-as-pi-tool.md` F.4).
- **POC de calibración**: el research exige validar accuracy antes de promover. Los
  consumidores hoy usan el guardarraíl como metadata, no como gate bloqueante.
