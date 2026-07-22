# ARD: compensation report skill

**Plan:** `2026-07-11-feature-compensation-report-skill`
**Status:** ✅ implemented

## Architectural decision

Single, self-contained skill, with no runtime dependencies on other
skills in the repo. It lives in `domain/compensation-report/` because:

- It is a loop with a concrete deliverable (a markdown file) → `domain`
  layer by repo convention (see AGENTS.md §3, §4).
- It does not orchestrate other loops of the SDD pipeline
  (`grill`, `plan`, `build`) → not `process`.
- It is not a support leaf (it is not invoked by other skills) → not
  `utility`.

## Layers and interfaces

```
+-------------------------+
| User (human)            |
| "I need a report"       |
+----------+--------------+
           |
           v
+-------------------------+
| compensation-report     |  ← loop skill, invocation: user
| (domain)                |
+----------+--------------+
           |
           v
+-------------------------+
| External research       |  ← web search, page extraction
| (web search/extract)    |
+-------------------------+
           |
           v
+-------------------------+
| Triangulation + compute |  ← in agent memory
+-------------------------+
           |
           v
+-------------------------+
| Markdown report         |  ← file written to home
+-------------------------+
```

## Layers (Layer 2 domain, AGENTS.md §3)

| Layer | Skill invoked | Reason |
|---|---|---|
| L3 utility | none in this flow | Does not require caveman or bootstrap |
| L2 domain | none in this flow | Does not consume use-clickup, make-a-diagram, etc. |
| L1 process | never | Per §3, domain MUST NOT invoke process |

## Input interfaces

| Name | Type | Required | Notes |
|---|---|---|---|
| `cargo` | string[] | yes | one or more target roles |
| `experiencia_anos` | number | yes | total years of experience |
| `ubicacion` | string | yes | city/country + modality |
| `empresa_objetivo` | string | yes | name or "general market" |
| `stack` | string[] | no | standout tools or skills |
| `salario_actual` | number | no | to compute the delta |
| `tipo_contratacion` | enum | no | default: empleado_directo |
| `moneda` | enum | no | default: ambas |
| `ciudades` | string[] | no | default: full country |
| `nivel` | enum | no | default: inferred from years |
| `sector` | string | no | default: general market |
| `beneficios_actuales` | string[] | no | default: typical benefits |

## Output interface

A single markdown file with:

- 7 mandatory sections in fixed order
- Salary tables always with 4 columns: USD/year, USD/month, COP/year,
  COP/month
- ≥ 3 sources per published percentile
- ≥ 10 total sources cited across §2, §3 and §7
- Header with exchange rate and date
- Actionable warnings, not generic

## Persistent data

None. The skill does not write databases, does not maintain caches,
does not generate logs. The report is the only artifact.

## Architectural risks

- **Coupling to the adapter's search tools.** The skill describes
  behavior ("research sources") without naming the tool. The Layer 4
  adapter decides whether to use `web_search`, `WebFetch`, `Brave
  Search`, or another. Reason: AGENTS.md §9 (agnosticism).
- **Exchange-rate variability between sources.** Different APIs
  return slightly different rates. Mitigation: the skill requires a
  single rate per report, recorded at the top, captured from the
  same research thread.
- **Lack of sources for emerging roles** (e.g. "Analytics Manager"
  in Latam is a new title). Mitigation: if there are not ≥ 3
  sources, fall back to the general market and warn.

## Required changes in other files

- `domain/compensation-report/SKILL.md` (new, 307 lines, < 500 ✓)
- `docs/plans/2026-07-11-feature-compensation-report-skill/` (new,
  this plan)
- `manifest.py` regenerates automatically when running `skill-forge`.

## Rejected decisions

- **Skill as utility (not domain).** Rejected: it has a concrete
  deliverable; it is not a support skill.
- **Split into 2 skills (interview + research).** Rejected: the
  interview is trivial (12 fields) and splitting adds ceremony
  without value (§11 right-size).
- **Output in HTML in addition to markdown.** Rejected: AGENTS.md §6
  says "artifacts are markdown, HTML only when the user asks
  ad-hoc".
