---
name: spec
description: |
  Detailed technical specification. Turn a PRD/ARD into a precise SPEC.md: exact
  schemas, algorithms, data shapes, edge cases, acceptance criteria. Sole mutator
  of SPEC.md in the active plan. Has NEW / AMEND / DISTILL modes.
  Use when the objective needs more detail than the ARD before planning, after
  design, or when the user says "spec this", "detailed spec", "specify the behavior".
invocation: user
layer: process
loop: spec
deliverable: SPEC.md in the active plan folder
metadata:
  version: "1.0.0"
---

# spec — PRD/ARD into SPEC.md

Detailed technical specification. The sole mutator of `SPEC.md` in the active
plan. Turns the PRD's requirements and the ARD's decisions into a precise spec:
exact schemas, algorithms, data shapes, edge cases, acceptance criteria.

Spec is the right-size step between design and plan. Not every objective needs a
SPEC — a small feature can go straight from PRD to PLAN (§11). Use spec when the
behavior is detailed enough that tasks alone would leave ambiguity.

## OWNERSHIP

Owns: `SPEC.md` in the active plan folder.
Reads: `PRD.md`, `ARD.md` (if present), `CONTEXT.md`, the codebase.
Hands off to: `plan` (→ `PLAN.md`).
MUST NOT write `PRD.md`, `ARD.md`, `PLAN.md`, or `LESSONS.md`.

`lessons` (auto) appends to `SPEC.md` `§V` when a bug is found during build —
spec allows that append (it owns the section, lessons is the sanctioned writer
of bug-driven invariant additions). `review` may harden `§V` (propose, not
silent rewrite).

## WHEN (user-invoked)

- After `design` produced an `ARD.md`, when detailed behavior is needed.
- After `grill` on a detailed-but-not-architectural objective (skip design).
- User says "spec this", "detailed spec", "specify the behavior", "write the spec".
- Existing `SPEC.md` needs a targeted amendment.

## STEP 0 — READ EXISTING STATE + DISPATCH

1. Resolve the active plan per §6. If none, ask the user to run `grill` first.
2. Read `PRD.md` (and `ARD.md` if present), `CONTEXT.md`, the relevant code.
3. Dispatch on request + plan state:

| State | Request | Mode |
|---|---|---|
| No `SPEC.md`, args describe idea/behavior | "spec this" | **NEW** |
| No `SPEC.md`, `from-code` in args | "distill spec from code" | **DISTILL** |
| `SPEC.md` exists, args start `amend` | "amend §V.3" | **AMEND** |
| `SPEC.md` exists, no args | — | ask user which mode |

## MODE: NEW — PRD/ARD into SPEC

Input: `PRD.md` (required), `ARD.md` (optional). If the PRD is fuzzy, stop and
recommend `grill` first.

1. **Goal** — copy `PRD.md §G` one-liner into `SPEC.md §G`.
2. **Constraints** — copy `PRD.md §C` + any `ARD.md` constraints into `§C`.
3. **Interfaces** — from `ARD.md §I` (or derive from PRD), write exact shapes:
   - `api: POST /x -> 200 {id:string}` with full request/response schemas.
   - `cmd: foo bar <arg> -> stdout JSON` with exit codes.
   - `env: FOO_KEY MUST be set` with type/format.
   - `file: config.yaml` schema.
4. **Invariants** — from `ARD.md §V` (or derive), write testable rules. Each
   invariant MUST be assert-able or grep-able. Number monotonic `V1, V2, ...`.
5. **Algorithms** — for non-trivial logic, write the algorithm in caveman
   pseudocode or a small state machine. Trim to the decision-rich parts.
6. **Edge cases** — enumerate inputs that break the happy path. Each edge case
   maps to an invariant or an explicit rejection rule.
7. **Acceptance criteria** — list the observables that prove the spec is met.
   Each criterion cites the invariant(s) it proves: `AC1 -> V1, V3`.
8. **Tasks section** — leave empty; `plan` writes `PLAN.md` separately. SPEC's
   job is behavior, not task breakdown.

Write to `SPEC.md` using `caveman`. Show the user the full file. Ask: "spec OK?"

## MODE: DISTILL — code into SPEC

Walk the repo. Produce `SPEC.md` by inferring:
- `§G` from README / package manifest / main entry.
- `§C` from the stack (deps, language, build).
- `§I` by enumerating public APIs / CLIs / configs / env vars.
- `§V` by deriving from tests and assertions.
- `§E` edge cases from any `?` items or known TODOs.

Caveman everywhere. Flag uncertain items with `?` so the user can confirm. This
is the right mode when there is code but no spec and the user wants to anchor
future work to documented current behavior.

## MODE: AMEND — targeted edit

Input: `amend §V.3` or `amend §I` etc.

Read that section. Show current. Ask the user what changes. Write. Show diff.

MUST NOT silently rewrite sections the user did not name. Sectioned ownership.

## OUTPUT RULES

- `caveman` format per the `caveman` skill.
- Preserve identifiers, paths, code, numbers, error strings verbatim.
- Numbering monotonic — never reuse `V.N` or `B.N`.
- Every invariant MUST be testable (assert-able or grep-able).
- Every interface shape MUST be exact (full schema, not "an object").
- Use `CONTEXT.md` canonical terms throughout.

## RIGHT-SIZE

A one-line fix gets no SPEC — go straight to `plan`. A small feature with an
obvious shape gets a thin SPEC (`§G` + `§I` + `§V`). Only genuinely uncertain
or high-blast-radius work gets the full set.

## WHEN TO STOP

Done when:
- `§G`, `§C`, `§I`, `§V` are written and the user agreed.
- Every invariant is testable and numbered.
- Every interface is exact.
- Edge cases map to invariants or explicit rules.
- Acceptance criteria cite invariants.
- New terms are in `CONTEXT.md`.

## HANDOFF

Tell the user: `plan` next (produces `PLAN.md` tasks, each citing the §V/§I it
serves and naming the test that proves it).

## BOUNDARIES

- MUST NOT rewrite `PRD.md` or `ARD.md`. Route back if they are wrong.
- MUST NOT write `PLAN.md` or `LESSONS.md`.
- MUST NOT guess a requirement. If the PRD is silent, park as `?` or route to `grill`.
- MUST show a diff before writing on AMEND.
- MUST use `caveman` and `CONTEXT.md` canonical terms.
