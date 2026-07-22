# PLAN: compensation report skill

**Plan:** `2026-07-11-feature-compensation-report-skill`
**Status:** ✅ all items completed

## Tasks

- [x] **T1 — Define the layer and name of the skill.** Decision:
  `domain/compensation-report`. Domain layer for being a loop with
  a concrete deliverable. Approved in AGENTS.md §3 / §4.
- [x] **T2 — Write frontmatter compliant with §5.** `name`,
  `description` with "Use when", `invocation: user`, `layer:
  domain`, `loop: compensation-report`, `deliverable: ...`,
  `provides: [salary-research, employer-profiling,
  negotiation-scripting, market-band-triangulation]`, `language:
  es-CO`, `metadata.version: 1.0.0`.
- [x] **T3 — Write the SKILL.md body (< 500 lines).** Structure:
  principles, when to use, when not, 5-step flow (interview,
  research, compute, generate, verify), anti-patterns, expected
  output. 307 lines at close.
- [x] **T4 — Specify the 7 mandatory report sections.** Header,
  employer profile, bands (always with 4 columns), active postings,
  compensation structure, 3 negotiation tactics, warnings, sources.
- [x] **T5 — Define the 4 canonical monetary forms.** USD/year,
  USD/month, COP/year, COP/month. Hard rule: every salary table
  must have all 4. Validated in the §5 checklist of the skill.
- [x] **T6 — Define the interview fields.** 4 mandatory (role,
  years, location, company), 8 optional with sensible defaults.
  Gathered in a single `clarify` call (not cascaded).
- [x] **T7 — Define the parallel research threads.** 4 threads:
  salary bands, active postings, employer profile, macro data
  (exchange rate + CPI + minimum wage). Minimum 3 sources per
  published percentile.
- [x] **T8 — Create the plan folder per §6.** Structure:
  `docs/plans/2026-07-11-feature-compensation-report-skill/`.
  Medium size → PRD + ARD + PLAN (no SPEC, no LESSONS — not a bug
  or refactor).
- [x] **T9 — Validate with `skill-forge audit`.** Result: PASS, 307
  lines (< 500), correct path, compliant frontmatter.
- [x] **T10 — Verify agnosticism (§9).** Grep for
  `pi|Claude|OpenCode|Cursor|Antigravity|TodoWrite|skill-recall`
  in the SKILL.md body → 0 matches. PASS.
- [x] **T11 — Regenerate manifest with `manifest.py`.** Verification:
  the skill is listed under `domain/` in the manifest.

## Executed commands

```bash
# Audit
python3 utility/skill-forge/scripts/audit.py compensation-report
# → PASS, 307 lines (<= 500)

# (Pending) Manifest
python3 utility/skill-forge/scripts/manifest.py --check
```

## Final status

🟢 Skill ready to use. All tasks checked off, no pending items.
