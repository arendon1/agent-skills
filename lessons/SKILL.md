---
name: lessons
description: |
  Bug to spec protocol. When a bug is found or a test fails during build, trace the
  root cause, decide whether a new invariant would catch recurrence, and append a
  lesson to the active plan's LESSONS.md. This is the reflex that stops classes of
  bugs from recurring.
  Use when a test fails, a bug is reported, a post-mortem is run, or a build
  verification fails.
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# lessons — bug → invariant reflex

Plan-then-execute fixes the code and forgets. This skill fixes the code AND
edits the spec so recurrence is impossible. That edit is the lesson.

Owns: `LESSONS.md` in the active plan + the invariant section (`§V`) of
`ARD.md` / `SPEC.md`. Appends only — never rewrites other sections.

## WHEN (self-trigger)

- A test failed during `build` verification.
- User reports a bug.
- Post-mortem after a production incident.
- `check` flags `VIOLATE` with root cause found.
- `verify` fails before declaring work complete.

Active plan resolved per constitution §6 (user names it, context matches slug,
most-recently-modified, then ask).

---

## SIX STEPS

### 1. TRACE

Read the failure output / bug report. Find the exact `file:line` of wrong
behavior. Name the root cause in one caveman sentence.

```
mw.go:47 rejects token exactly at expiry boundary
=> token < not <= compared against current_time
```

### 2. ANALYZE

Ask three questions:

- Would a new `§V` invariant catch this class of bug? (most common: yes)
- Is `§I` wrong — did the spec claim a shape the code cannot deliver? (sometimes)
- Is `§T` wrong — did we build the wrong thing? (rare but real)

### 3. PROPOSE

Draft the spec change. Never skip the `LESSONS.md` bug row; the `§V` invariant
in `ARD.md`/`SPEC.md` is case-by-case.

Template (caveman, per the `caveman` skill):

```
LESSONS.md §B row: B<next>|<date>|<root cause>|<invariant ref>
ARD.md/SPEC.md §V line: V<next>: <testable rule that would have caught it>
```

Example:

```
B3|2026-06-28|refund job ran twice on retry|V7
V7: MUST check idempotency key before charge reversal, every refund
```

### 4. GENERATE TEST

A new invariant without a test is a lie. Add the failing test first. Name the
test so it cites the invariant: `TestV7_RefundIdempotent`.

### 5. VERIFY

Fix the code. Run the test. MUST pass. Run the full suite. MUST NOT regress.

### 6. LOG

Commit the spec edit + test + code fix together.

```
backprop §B.<n> + §V.<N>: <one-line cause>
```

Example: `backprop §B.3 + §V.7: refund retry not idempotent`.

---

## WHAT MAKES A GOOD INVARIANT

- Testable in code (grep-able or assert-able).
- Scoped to a behavior, not a file.
- Stated positively when possible (`MUST hold` over `NEVER forbid`).
- References the `§I` surface where it applies.

**Bad:** `V8: code should be correct.`
**Good:** `V8: every pg_query MUST use driver params, NEVER string concat.`

---

## WHEN NOT TO ADD §V

Still append the `§B` bug row — record that this failure mode was considered.
But skip the new invariant when:

- Bug was a purely mechanical typo with no class (`i++` vs `i--` in throwaway).
- Fix is a one-time migration.
- Root cause is an external dep (upgrade deps instead, note in `§C`).

Future bug with the same smell → `LESSONS.md` search shows precedent.

---

## LESSONS.md FORMAT

Each plan's `LESSONS.md` is a bug log + invariant index. Invariants live in
`ARD.md`/`SPEC.md` `§V`; `LESSONS.md` references them so the bug history is
grep-able in one place.

```markdown
# LESSONS — <plan slug>

## §B BUGS

id|date|root cause|invariant|fix commit
B1|2026-06-28|token < not <=|V2|abc1234
B2|2026-06-28|race on write|V3|def5678
B3|2026-06-28|refund retry not idempotent|V7|-

## §V INVARIANTS (index)

Invariants live in ARD.md / SPEC.md. This section indexes them for search.

- V2: token expiry <= current_time => reject  [ARD.md §V.2]
- V3: DB write MUST be in transaction          [ARD.md §V.3]
- V7: MUST check idempotency key before charge reversal, every refund  [SPEC.md §V.7]
```

Table cell rules: literal `|` → escape as `\|`. Backticks OK. Cells trimmed.
Empty = `-`. Status of a fix: commit hash, or `-` if not yet fixed.

---

## OUTPUT SHAPE

Every `lessons` run produces:

1. `LESSONS.md` `§B` entry (always).
2. `ARD.md`/`SPEC.md` `§V` entry (usually).
3. Test file (when `§V` added).
4. Code fix.
5. One commit (spec edit + test + fix together).

No dashboards. No log files. `LESSONS.md` + git is the full history.

---

## RIGHT-SIZE

A one-line typo fix with no class → `§B` row only, no `§V`. A recurring class
of bug → full six-step protocol. Ceremony scales to blast radius, never ego
(constitution §11).
