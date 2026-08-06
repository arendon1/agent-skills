# PLAN — use-mineru-cloud

Status cells: `[x]` done, `[ ]` pending.

| # | Task | Test / proof | Status |
|---|------|--------------|--------|
| T1 | PRD + PLAN artifacts | files exist | [x] |
| T2 | `scripts/convert.py` — SDK wrapper (auth/convert/batch/flash/crawl) | local dry-run: `--help`, auth-check with token | [x] |
| T3 | `references/api.md` — verified contract (endpoints, limits, errors, SDK API) | file exists, matches RESEARCH.md | [x] |
| T4 | `SKILL.md` — frontmatter, triggers, workflow, boundaries | `skill-forge audit` PASS | [x] |
| T5 | Commit (conventional) | commit after audit | [x] |
| T6 | Deploy to phone (`~/.agents/skills/`) + live E2E via ssh | real PDF → md on device | [x] |
| T7 | Cleanup phone artifacts + `LESSONS.md` | no leftovers on phone | [x] |
| T8 | Close ClickUp task (move status `complete` + comment) | task closed | [x] |
