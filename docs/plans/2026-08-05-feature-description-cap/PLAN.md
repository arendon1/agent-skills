# PLAN — Description cap 1024 + floor 200

Vertical slices. Proof per task = named check. Status cells owned by `build`.

## Tasks

| id | status | task | cites |
|----|--------|------|-------|
| T1 | [ ] | audit.py: `MAX_DESC_CHARS = 1024` (FAIL if exceeded), `MIN_DESC_CHARS = 200` (WARN if below), keep "Use when"/"Usa cuando" check. Synthetic test: >1024 FAIL, <200 WARN, 200..1024 clean. | R1,R2,R6 |
| T2 | [ ] | AGENTS.md §5 field requirements + §15 constraints: description 1..1024 (MUST), >= 200 (SHOULD), front-load trigger phrase. | R3,R5 |
| T3 | [ ] | Rewrite `use-clickup` description: 140 -> 300..500 chars, front-loaded "Use when". | R4 |
| T4 | [ ] | Rewrite `gestionar-cursos` description: 194 -> 300..500, es-CO, "Usa cuando". | R4 |
| T5 | [ ] | Rewrite `skill-forge` description: 208 -> 300..500, front-loaded "Use when". | R4 |
| T6 | [ ] | Rewrite `research-literature` description: 254 -> 300..500, es-CO. | R4 |
| T7 | [ ] | Rewrite `generar-paper` description: 275 -> 300..500, es-CO. | R4 |
| T8 | [ ] | ADR-0002 (why 1024 not 1200, harness table) + gate: full audit sweep --strict 0/0, desc length scan (all 1..1024, >=200), manifest --check, conventional commits, push. | R7 |

## Order & dependencies

- T1 first (enforcement exists before rewrites). T2 after T1 (constitution
  matches enforcer). T3..T7 independent, parallelizable. T8 blocked by all.

## Proof per task

- T1: `audit` on a synthetic >1024 desc -> FAIL; <200 -> WARN; run against
  repo: 9 existing skills WARN (<200) before rewrites, 0 FAIL.
- T2: grep AGENTS.md for "1024" + "200" + "front-load".
- T3..T7: `audit <skill> --strict` PASS (0 warnings) && python len check in
  300..500 && desc starts with "Use when"/"Usa cuando" && language un-mixed.
- T8: `ls docs/adr/0002-*.md` && full sweep `--strict` exit 0 && length scan
  all in 1..1024 with 0 <200 && `manifest.py --check` exit 0 && push.

## Stop conditions

- Any FAIL in audit sweep -> fix before proceeding (constitution gate).
- Rewrite exceeds 1024 -> trim to <= 500 target.
- es-CO skill gains English words -> redo in single language (§5).
- User's original 1200 requested -> already resolved: 1024 (see PRD background).

## Right-size

Small-medium feature: constitutional + enforcement + 5 rewrites + ADR.
Artifacts: PRD + PLAN. No ARD (no architecture change).
