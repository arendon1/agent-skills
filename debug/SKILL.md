---
name: debug
description: |
  Disciplined diagnosis loop for hard bugs and performance regressions. Build a
  tight feedback loop first, reproduce, minimize, hypothesize, instrument, fix,
  regression-test. Never guess at a fix before root cause is found.
  Use when the user says "diagnose" or "debug this", or reports something
  broken, throwing, failing, or slow, or when a build verification fails.
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# debug — disciplined diagnosis

A discipline for hard bugs and performance regressions. Random fixes waste time
and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes
are failure. Skip phases only when explicitly justified.

## WHEN (self-trigger)

- User says "diagnose", "debug this", "why does this", "broken", "failing", "slow".
- A test fails during `build` and `tdd` didn't catch it as a simple fix.
- A regression is reported.
- A build verification fails.
- User reports a bug or shares a stack trace.

Use ESPECIALLY when:
- Under time pressure (emergencies make guessing tempting).
- "Just one quick fix" seems obvious.
- You've already tried multiple fixes.
- Previous fix didn't work.
- You don't fully understand the issue.

## THE IRON LAW

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes. If you catch yourself
reading code to build a theory before a red-capable command exists, stop — jumping
straight to a hypothesis is the exact failure this skill prevents.

## THE SIX PHASES

You MUST complete each phase before proceeding to the next.

### Phase 1 — Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a **tight**
pass/fail signal for the bug — one that goes red on *this* bug — you will find the
cause. If you don't have one, no amount of staring at code will save you.

Spend disproportionate effort here. Be aggressive. Be creative. Refuse to give up.

Ways to construct a loop, in roughly this order:
1. Failing test at whatever seam reaches the bug (unit, integration, e2e).
2. HTTP script against a running dev server.
3. CLI invocation with a fixture input, diffing stdout against a known-good snapshot.
4. Headless browser script driving the UI, asserting on DOM/console/network.
5. Replay a captured trace (saved request/payload/event log through the code path).
6. Throwaway harness — minimal subset of the system exercising the bug code path.
7. Property/fuzz loop — run 1000 random inputs and look for the failure mode.
8. Bisection harness — automate "boot at state X, check, repeat" for `git bisect`.
9. Differential loop — same input through old vs new version, diff outputs.
10. Human-in-the-loop bash script — last resort, drive the human with a structured loop.

**Tighten the loop** (treat it as a product):
- Faster? (cache setup, skip unrelated init, narrow scope)
- Sharper signal? (assert on the specific symptom, not "didn't crash")
- More deterministic? (pin time, seed RNG, isolate filesystem, freeze network)

A 30-second flaky loop is barely better than no loop; a 2-second deterministic one
is a debugging superpower.

**Non-deterministic bugs:** the goal is not a clean repro but a higher reproduction
rate. Loop the trigger 100x, parallelize, add stress, narrow timing windows. A 50%
flake is debuggable; 1% is not — keep raising the rate.

**When you genuinely cannot build a loop:** stop and say so explicitly. List what
you tried. Ask the user for (a) access to an environment that reproduces it, (b) a
captured artifact (HAR, log dump, core dump, screen recording), or (c) permission
to add temporary production instrumentation. Do NOT proceed to hypothesize.

**Completion criterion — a tight loop that goes red:** phase 1 is done when the loop
is tight and red-capable: you can name ONE command — a script path, a test
invocation — that you have already run at least once (paste the invocation and its
output), and that is:
- [ ] Red-capable — drives the actual bug code path and asserts the user's exact
  symptom; can go red on this bug and green once fixed.
- [ ] Deterministic — same verdict every run (flaky: pinned high reproduction rate).
- [ ] Fast — seconds, not minutes.
- [ ] Agent-runnable — runs unattended.

### Phase 2 — Reproduce + minimize

Run the loop. Watch it go red. Confirm:
- [ ] The loop produces the failure mode the user described — not a different
  failure nearby. Wrong bug = wrong fix.
- [ ] Reproducible across multiple runs (or at a high enough rate for flakes).
- [ ] You captured the exact symptom (error message, wrong output, slow timing)
  so later phases can verify the fix addresses it.

**Minimize:** shrink the repro to the smallest scenario that still goes red. Cut
inputs, callers, config, data, steps one at a time, re-running the loop after each
cut — keep only what is load-bearing. A minimal repro shrinks the hypothesis space
and becomes the clean regression test in phase 5. Done when every remaining element
is load-bearing (removing any one makes the loop go green).

Do not proceed until you have reproduced AND minimized.

### Phase 3 — Hypothesize

Generate **3-5 ranked hypotheses** before testing any. Single-hypothesis
generation anchors on the first plausible idea.

Each hypothesis MUST be **falsifiable**: state the prediction it makes.

```
If <X> is the cause, then <changing Y> will make the bug disappear /
<changing Z> will make it worse.
```

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen.

Show the ranked list to the user before testing. They often have domain knowledge
that re-ranks instantly, or know hypotheses they've already ruled out. Cheap
checkpoint, big time saver. Don't block — proceed with your ranking if the user is
away.

### Phase 4 — Instrument

Each probe MUST map to a specific prediction from phase 3. Change one variable at
a time.

Tool preference:
1. Debugger / REPL inspection if the env supports it. One breakpoint beats ten logs.
2. Targeted logs at the boundaries that distinguish hypotheses.
3. NEVER "log everything and grep".

Tag every debug log with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup becomes a
single grep. Untagged logs survive; tagged logs die.

**Perf branch:** for performance regressions, logs are usually wrong. Instead:
establish a baseline measurement (timing harness, profiler, query plan), then
bisect. Measure first, fix second.

### Phase 5 — Fix + regression test

Write the regression test BEFORE the fix — but only if there is a correct seam.

A correct seam exercises the **real bug pattern** as it occurs at the call site.
If the only available seam is too shallow (single-caller test when the bug needs
multiple callers), a regression test there gives false confidence.

**If no correct seam exists, that itself is the finding.** Note it. The codebase
architecture is preventing the bug from being locked down. Flag this for the
`deepen` discipline.

If a correct seam exists:
1. Turn the minimized repro into a failing test at that seam.
2. Watch it fail.
3. Apply the fix.
4. Watch it pass.
5. Re-run the phase 1 feedback loop against the original (un-minimized) scenario.

### Phase 6 — Cleanup + post-mortem

Required before declaring done:
- [ ] Original repro no longer reproduces (re-run the phase 1 loop).
- [ ] Regression test passes (or absence of seam is documented).
- [ ] All `[DEBUG-...]` instrumentation removed (grep the prefix).
- [ ] Throwaway prototypes deleted (or moved to a clearly-marked debug location).
- [ ] The hypothesis that turned out correct is stated in the commit / PR message.

**Then invoke the `lessons` reflex:** ask "what would have prevented this bug?" If
the answer is a new `§V` invariant, `lessons` appends it. If the answer involves
architectural change (no good test seam, tangled callers, hidden coupling), hand
off to the `deepen` discipline with the specifics — make the recommendation after
the fix is in, not before.

## BOUNDARIES

- MUST NOT propose fixes before phase 1 (root cause investigation).
- MUST complete each phase before the next.
- MUST generate 3-5 ranked hypotheses, not single-hypothesis.
- MUST tag debug logs with a unique prefix and remove them in phase 6.
- MUST write the regression test before the fix (when a correct seam exists).
- MUST invoke `lessons` after the fix is in.
- MUST state the correct hypothesis in the commit message.
