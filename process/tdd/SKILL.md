---
name: tdd
description: |
  Test-driven development. Write the test first, watch it fail, write minimal code
  to pass, refactor. Vertical slices via tracer bullets — one test to one
  implementation, never all-tests-then-all-code. Tests verify behavior through
  public interfaces, not implementation.
  Use when implementing any feature or bugfix, before writing implementation code,
  or when the user says "implement", "build this", "add a feature".
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# tdd — red, green, refactor

Write the test first. Watch it fail. Write minimal code to pass. Refactor.

**Core principle:** if you didn't watch the test fail, you don't know if it tests
the right thing. Production code without a failing test first is a lie.

## WHEN (self-trigger)

Always, when implementing any feature or bugfix, before writing implementation code:
- New features, bug fixes, refactoring, behavior changes.
- Invoked by the `build` loop per task.

Exceptions (ask the user):
- Throwaway prototypes.
- Generated code.
- Configuration files.

Thinking "skip TDD just this once"? Stop. That is rationalization.

## THE IRON LAW

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over. Don't keep it as "reference",
don't "adapt" it while writing tests, don't look at it. Delete means delete.
Implement fresh from tests.

## PHILOSOPHY

**Good tests** verify behavior through public interfaces, not implementation
details. Code can change entirely; tests shouldn't. A good test reads like a
specification — "user can checkout with valid cart" tells you exactly what
capability exists. These tests survive refactors because they don't care about
internal structure.

**Bad tests** are coupled to implementation. They mock internal collaborators,
test private methods, or verify through external means (querying a database
directly instead of using the interface). Warning sign: your test breaks when
you refactor, but behavior hasn't changed. If you rename an internal function and
tests fail, those tests were testing implementation, not behavior.

## ANTI-PATTERN: HORIZONTAL SLICES

DO NOT write all tests first, then all implementation. This is "horizontal
slicing" — treating RED as "write all tests" and GREEN as "write all code."

This produces **crap tests**:
- Tests written in bulk test *imagined* behavior, not *actual* behavior.
- You test the *shape* of things (data structures, function signatures) rather
  than user-facing behavior.
- Tests become insensitive to real changes — they pass when behavior breaks,
  fail when behavior is fine.
- You outrun your headlights, committing to test structure before understanding
  the implementation.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED -> GREEN: test1 -> impl1
  RED -> GREEN: test2 -> impl2
  RED -> GREEN: test3 -> impl3
  ...
```

## WORKFLOW

### 1. Planning

Read `CONTEXT.md` if it exists so test names and interface vocabulary match the
project's domain language. Respect any ADRs in the area you are touching.

Before writing any code:
- Confirm with the user what interface changes are needed.
- Confirm with the user which behaviors to test (prioritize).
- Identify opportunities for deep modules (small interface, deep implementation).
- List the behaviors to test (not implementation steps).
- Get the user's approval on the plan.

Ask: "What should the public interface look like? Which behaviors are most
important to test?"

You can't test everything. Confirm with the user exactly which behaviors matter
most. Focus testing effort on critical paths and complex logic, not every
possible edge case.

### 2. Tracer bullet

Write ONE test that confirms ONE thing about the system:

```
RED:   write test for first behavior -> test fails
GREEN: write minimal code to pass -> test passes
```

This is your tracer bullet — proves the path works end-to-end.

### 3. Incremental loop

For each remaining behavior:

```
RED:   write next test -> fails
GREEN: minimal code to pass -> passes
```

Rules:
- One test at a time.
- Only enough code to pass the current test.
- Don't anticipate future tests.
- Keep tests focused on observable behavior.

### 4. Refactor

After all tests pass, look for refactor candidates:
- Extract duplication.
- Deepen modules (move complexity behind simple interfaces).
- Apply SOLID principles where natural.
- Consider what new code reveals about existing code.
- Run tests after each refactor step.

**Never refactor while RED.** Get to GREEN first.

## CHECKLIST PER CYCLE

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```

## BOUNDARIES

- MUST write the test first and watch it fail.
- MUST write minimal code to pass — no speculative features.
- MUST use vertical slices (one test -> one implementation), never horizontal.
- MUST test behavior through public interfaces, not implementation.
- MUST NOT refactor while RED.
- MUST read `CONTEXT.md` and use canonical terms in test names.
