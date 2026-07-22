# PRD: compensation report skill

**Plan:** `2026-07-11-feature-compensation-report-skill`
**Type:** feature
**Status:** ✅ implemented

## Context

The user is a BI/Analytics engineer with 6 years of experience in
Colombia, remote, specialized in Tableau. They need to negotiate
salary frequently (annual reviews, external offers) and did not have
a reproducible flow to produce actionable market analyses. The manual
conversation (asking for data, doing searches, generating tables) took
3-4 turns and the reports were lost in the chat.

## Problem

1. Collecting the data needed for a compensation analysis required
   2-3 turns of questions.
2. The research of salary bands in LATAM (COP + USD, multi-role,
   multi-stack) was not standardized — it depended on the agent's
   memory.
3. The final report varied in form: sometimes in columns, sometimes
   in prose, sometimes only USD without COP conversion.
4. There was no separation between "generated report" and "reusable
   report" — every negotiation started from zero.

## Users

- **Primary:** the user themselves, negotiating salary with their
  current employer or evaluating external offers.
- **Secondary:** other LATAM professionals in similar technical
  roles who adopt the skill via the `agent-skills-v2` repo.

## Goals

1. Reduce the "I need a compensation analysis" cycle to 2 turns:
   one for the interview, one for the ready report.
2. Standardize the report: always 7 sections, always 4 forms of
   each figure (USD/year, USD/month, COP/year, COP/month), always 3+
   sources per percentile.
3. Make the report reusable as an artifact: a versionable markdown
   file, not ephemeral chat.
4. Make the skill harness-agnostic (runs on any Layer 4 adapter that
   can read SKILL.md and run Bash).

## Non-goals

- Does not try to predict individual offers — only reflects the
  available public market.
- Does not scrape non-public sites (authenticated Glassdoor, private
  levels, etc.).
- Does not produce legal or tax recommendations.
- Does not automate sending the offer to the employer — the report
  ends with the user, not the recruiter.

## Success criteria

- The user can invoke the skill, answer the interview, and receive
  a markdown report in less than 5 minutes.
- The report always has the 4 monetary columns per salary table.
- The report cites at least 10 external sources.
- The skill passes `skill-forge audit` without critical warnings.
- The skill is agnostic: it does not mention `pi`, `Claude Code`,
  `OpenCode`, or slash-command syntax in the body.

## Risks

- **Stale data:** salary bands change quarter to quarter.
  Mitigation: the skill requires a date on each source and warns
  when they are older than 12 months.
- **Volatile exchange rate:** the COP/USD rate varies. Mitigation:
  the report records the exchange rate used with a date and warns
  about FX risk if the contract is in COP.
- **High source variance:** Glassdoor has huge outliers. Mitigation:
  mandatory triangulation of 3 sources, explicit warning if
  intra-percentile variance exceeds 25%.
- **False precision:** a P50 percentile does not guarantee anything.
  Mitigation: the report is about the market, not an individual
  offer; the negotiation tactics make that clear.
