# PLAN — Process-layer Tier 1

Vertical slices. Each task names its proof (test). Status cells owned by
`build`; flip `[x]` only with fresh verification (§verify).

## Tasks

| id | status | task | cites |
|----|--------|------|-------|
| T1 | [x] | Extract `process/grilling/SKILL.md` (auto): frontier/rounds algorithm, numbered questions + recommended answers, facts-are-agent's-job with non-blocking subagent dispatch, done-when-frontier-empty. Refactor `process/grill/SKILL.md` to invoke grilling; keep plan-folder + PRD.md ownership. Add `frontier` + `grilling` terms to CONTEXT.md. | V1,V2,V3,V4,V8 |
| T2 | [x] | Rewrite `process/review/SKILL.md` to two-axis: Standards + Spec as parallel subagents (isolated contexts), Fowler 12-smell baseline as in-file reference, side-by-side report (`## Standards`/`## Spec`), keep REFUTE + go/no-go gate. | V1,V2,V5,V8 |
| T3 | [ ] | Add `process/wait-what/SKILL.md` (auto): re-pitch corrective. Uses CONTEXT.md vocabulary, plain language, short. No artifact writes. | V1,V2,V3,V7,V8 |
| T4 | [ ] | Add `process/to-questionnaire/SKILL.md` (user, loop: to-questionnaire, deliverable: questionnaire file) + `references/template.md`. Grills the send (recipient, what-needs-back), targets the gap, writes `to-questionnaire-<slug>.md` in cwd. | V1,V2,V3,V6,V8 |
| T5 | [ ] | Patch `process/debug/SKILL.md`: (a) no-correct-seam = architectural finding (documented, post-fix handoff), (b) `[DEBUG-<suffix>]` tagged logs with one-grep cleanup, (c) ranked falsifiable hypotheses shown to user before testing. | V1,V2,V10,V8 |
| T6 | [ ] | ADR + out-of-scope infra: `docs/adr/0001-politicas-from-soul.md` (migrate POLÍTICA v1-v10, decision+rationale+date), `.out-of-scope/mattpocock-deferred-tier2.md` (rejected-from-Matt list + why), AGENTS.md §6 ADR convention line. | V9 |
| T7 | [ ] | Gate: run audit on all touched skills (T1-T5), `manifest.py` + `--check`, grep agnosticism (§9) over new bodies, verify CONTEXT.md/AGENTS.md edits, conventional commit. | V1,V8,V9 |

## Order & dependencies

- T1..T6 independent (different files). T7 blocked by all.
- T1 first if sequencing manually (grill is the daily driver; wait-what/
  to-questionnaire are additive, no ordering pressure).

## Proof per task

- T1: `audit grilling --strict` PASS && `audit grill --strict` PASS && grep
  grill body for frontier algorithm (no re-implementation) && CONTEXT.md has
  `frontier` entry.
- T2: `audit review --strict` PASS && body contains two subagent prompts +
  smell baseline + gate section.
- T3: `audit wait-what --strict` PASS && body triggers on confusion signals.
- T4: `audit to-questionnaire --strict` PASS && template file exists under
  references/ && body declares loop+deliverable.
- T5: `audit debug --strict` PASS && body contains no-seam finding, DEBUG-
  tag, ranked-hypotheses gate.
- T6: `ls docs/adr/0001-*.md` && `ls .out-of-scope/` non-empty && AGENTS.md
  §6 mentions docs/adr/.
- T7: `manifest.py --check` exit 0 && full `audit` sweep PASS && git log
  shows one conventional commit per task or single wrap commit.

## Completion

- ALL tasks `[x]` + T7 gate green => **archive the folder** to
  `docs/plans/archive/2026-08-05-refactor-process-tier1/` per §6.
  Do not close the plan in place. (User instruction: "don't forget to
  open it when finished" = archive on completion.)

## Stop conditions

- Any audit FAIL -> fix before proceeding (constitution hard gate).
- grilling extraction changes grill UX (loses plan-folder/PRD behavior) ->
  revert extraction, keep primitive additive.
- POLÍTICA memory inaccessible -> write what is reconstructible, mark gaps.

## Right-size

Medium refactor: 6 work items, 5 skills touched + infra. Artifacts:
PRD + ARD + PLAN. No SPEC — behaviors pinned by this plan + the originals
(mattpocock/skills at /tmp/mattpocock-skills).
