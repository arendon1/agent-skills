---
name: grilling
description: |
  Relentless interview primitive: map the design tree, work the frontier in
  rounds — every question whose prerequisites are settled gets asked in one
  round, numbered, each with a recommended answer. Facts are the agent's job,
  never the user's. Use when any loop needs to sharpen a fuzzy idea by
  interview (grill, triage, deepen, wayfinder), or when the user asks to be
  grilled, stress-tested, or challenged.
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# grilling — the interview primitive

Interview engine. Runs the conversation that turns fuzz into decisions.
Owns nothing, writes nothing: no PRD, no CONTEXT.md, no plan folder. The
calling loop owns artifacts. Pure protocol, reusable by any loop that must
sharpen an idea by interview.

## THE MODEL

Map the discussion as a **design tree**: every decision branches into the
decisions that hang off it.

- **Frontier** — every decision whose prerequisites are settled: the questions
  askable NOW without guessing answers you have not heard yet.
- **Round** — ask the WHOLE frontier in ONE round. Number each question, give
  your recommended answer for each. Wait for all answers.
- **Recompute** — answers reshape the tree: settled decisions push the frontier
  outward and unblock questions that depended on them. Next round asks the new
  frontier.
- A question whose answer depends on another question still open this round
  belongs to a LATER round, not this one.

Done when the frontier is empty: every branch visited, nothing silently
assumed. Do not act until the user confirms shared understanding.

## FACTS ARE YOUR JOB, DECISIONS ARE THE USER'S

- Frontier question needs a fact from the environment (filesystem, tools,
  external source)? Look it up yourself. NEVER ask the user anything you can
  find.
- Expensive lookup? Delegate to a background helper and DO NOT block the
  round: a running exploration is an unsettled prerequisite, so only the
  questions downstream of it wait — ask the rest of the frontier now.
- The DECISIONS are the user's. Put each to them and wait.

## QUESTION FORMAT

Each question carries your recommended answer so the user can grunt "yes"
and move:

```
Q<n> — <title>: <body, may list multiple choices>
rec: <your recommendation>
```

Fuzzy or overloaded term surfaces mid-interview? Coin a canonical term and
hand it to the calling loop to write into its glossary — do not write it
yourself (you own no artifacts).

## BOUNDARIES

- MUST NOT write any artifact (plan folder, PRD, glossary, file).
- MUST NOT decide for the user — recommend, then wait.
- MUST NOT block a round on a fact lookup — ask the rest of the frontier.
- MUST NOT re-ask settled decisions.
- MUST NOT act on the interview until the user confirms shared understanding.
