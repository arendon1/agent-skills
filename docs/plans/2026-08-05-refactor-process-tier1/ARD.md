# ARD — Process-layer Tier 1 architecture

## Goal

Extract 4 reusable mechanics into process layer, add 2 infra conventions.
Everything lands under §3 layers, §9 agnosticism, §5 frontmatter.

## I. Architecture decisions

### D1 — grilling as primitive, grill as stateful wrapper

- `process/grilling/SKILL.md` — **auto** discipline. Owns the interview
  algorithm ONLY. Zero artifact writes.
- `process/grill/SKILL.md` — **user** loop (unchanged contract: `loop: grill`,
  `deliverable: plan folder + PRD.md`). Runs grilling internally.
- Call rule: L1 -> L1 allowed (§3). grilling MUST NOT write plan folder/PRD;
  grill MUST NOT re-implement the frontier (invokes grilling).
- Why: other skills (`triage`, `deepen`, future `wayfinder`) run interviews
  without pulling plan-folder ceremony. Behavior triggers domain (§1.1).

**Interview algorithm (from mattpocock grilling):**
- Map design tree. Frontier = decisions whose prerequisites settled.
- Ask WHOLE frontier in one round: numbered questions + recommended answer
  each. Wait for answers. Recompute frontier. Repeat.
- Facts = agent's job, NEVER user's. Frontier question needs env fact ->
  dispatch subagent, DON'T block: ask rest of frontier now.
- Done when frontier empty. Do not act until user confirms shared
  understanding.

### D2 — two-axis review

- `process/review/SKILL.md` keeps: REFUTE posture, evidence-cited findings,
  artifact ownership (reads only), go/no-go gate.
- Adds: two axes run as **parallel subagents** (isolated contexts):
  - Standards: repo-documented standards + Fowler 12-smell baseline (fixed
    in-file reference; repo standard overrides baseline; skip tooling-enforced).
  - Spec: originating spec compliance (missing/partial, scope creep, wrong
    implementation; quote spec line per finding).
- Aggregation: report under `## Standards` / `## Spec` verbatim, one-line
  summary per axis, worst issue each. NEVER merge/rerank across axes.
  Gate stays: BLOCK until both axes clear or user overrides.
- Smell baseline = in-file flat peer-set reference (per caveman: legit flat).

### D3 — new skills placement

| skill | layer | invocation | loop | deliverable | provides |
|-------|-------|-----------|------|-------------|----------|
| `wait-what` | process | auto | - | - | - |
| `to-questionnaire` | process | user | to-questionnaire | `to-questionnaire-<slug>.md` in cwd | - |

- `wait-what` self-triggers on confusion signal ("wait what", "I don't
  understand", "re-pitch"). Re-pitch MUST use CONTEXT.md vocabulary; plain
  language; short. No artifact writes.
- `to-questionnaire` grills the SEND not the subject: recipient role/
  expertise/relationship (1 exchange), what user needs back (1 exchange),
  then write questionnaire targeting the gap. Template in
  `references/template.md` (disclosed reference).

### D4 — debug deltas

- `process/debug/SKILL.md` gains:
  - Phase-5 output: no correct seam = THE finding. Document it; flag for
    architectural handoff (post-fix, per diagnosing-bugs sequencing).
  - Tagged logs: `[DEBUG-<suffix>]` prefix, cleanup = one grep.
  - Phase-3 gate: 3-5 falsifiable hypotheses, ranked, shown to user before
    testing (don't block on AFK user). Each states prediction.

### D5 — ADR + out-of-scope infra

- `docs/adr/NNNN-<slug>.md` — numbered ADRs for the skills system itself.
  Seed: `0001-politicas-migrated-from-soul.md` (POLÍTICA v1-v10 condensed:
  decision + rationale + date). Future: system-level decisions.
- `.out-of-scope/` at repo root — retired/rejected proposals. Seed:
  `mattpocock-rejected-t2.md` (wayfinder, writing-for-agents, docs pages,
  wizard, changesets — with one-line why deferred).
- `AGENTS.md` §6 gains one line: ADRs live in `docs/adr/NNNN-<slug>.md`;
  rejected proposals in `.out-of-scope/`.
- Durability rule: a system decision is only real when a repo file carries
  it — soul memory is not the source of truth (§10).

## V. Invariants

```
V1: new/changed SKILL.md MUST pass skill-forge audit --strict (exit 0)
V2: new/changed SKILL.md MUST stay < 500 lines (§15)
V3: frontmatter per §5; user-invoked MUST declare loop + deliverable
V4: grilling MUST NOT write plan folder / PRD.md / CONTEXT.md (grill owns)
V5: review MUST keep REFUTE + go/no-go; axes reported separate, never merged
V6: to-questionnaire output -> to-questionnaire-<slug>.md in cwd
V7: wait-what re-pitch MUST use CONTEXT.md vocabulary if file exists
V8: no harness/tool names in new/changed skill bodies (§9)
V9: ADR dir docs/adr/; rejected proposals .out-of-scope/ (repo root)
V10: debug hypothesis list MUST be falsifiable + ranked + shown to user
```

## I. Interfaces

```
cmd: python utility/skill-forge/scripts/audit.py <name> --strict -> exit 0
cmd: python utility/skill-forge/scripts/manifest.py --check -> exit 0
file: docs/adr/NNNN-<slug>.md -> ADR (decision, rationale, date)
file: .out-of-scope/<slug>.md -> retired proposal + why
file: to-questionnaire-<slug>.md -> questionnaire (user deliverable)
api: grilling frontier round -> numbered questions + recommended answers
```

## Data flow

```
grill (user) -> grilling (frontier rounds, facts via subagents) -> PRD.md
review -> [Standards subagent | Spec subagent] -> aggregated report -> gate
debug -> [loop -> repro -> hypotheses(user-checked) -> fix -> tagged logs
         -> no-seam? architectural handoff]
```

## Deliberately NOT adopted (with reason)

- Release machinery, dual manifests, ask-matt router, teach rewrite:
  no delta or no distribution need (§PRD out of scope).
- Their governance (prose trust, no validator): we keep skill-forge audit.
