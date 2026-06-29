---
name: teach
description: |
  Teach the user a new skill or concept over multiple sessions, using the current
  directory as a stateful teaching workspace. Build exercises, check understanding,
  adapt pace to the learner.
  Use when the user wants to learn something, not build something, or says "teach
  me", "I want to learn", "explain over time", "help me understand", "course on",
  "tutorial".
invocation: user
layer: process
loop: teach
deliverable: learned concept (captured in learning-records + reference materials)
metadata:
  version: "1.0.0"
---

# teach — stateful multi-session teaching

Teach the user a concept over multiple sessions. The current directory is a
stateful teaching workspace — the state of their learning is captured in files
there. Build exercises, check understanding, adapt pace to the learner.

This skill is for *learning*, not *building*. If the user wants to build something,
route to `grill` / `plan` / `build` instead.

## OWNERSHIP

Owns: the teaching workspace files (`MISSION.md`, `RESOURCES.md`, `learning-records/`,
`lessons/`, `reference/`, `NOTES.md`).
Reads: `CONTEXT.md` if it exists (for canonical terms in the teaching domain).
MUST NOT write plan artifacts. Teaching workspace is separate from plan artifacts.

## WHEN (user-invoked)

- User says "teach me", "I want to learn", "explain over time", "help me
  understand", "course on", "tutorial".
- User wants to learn a concept, not build something.

## THE TEACHING WORKSPACE

Treat the current directory as a teaching workspace. State is captured in:

- **`MISSION.md`** — the *reason* the user is interested in the topic. Grounds all
  teaching.
- **`./reference/*`** — reference materials: compressed learnings, cheat sheets,
  reference algorithms, syntax, glossaries. The raw units of learning. Beautiful
  documents that print well and are designed for quick reference.
- **`RESOURCES.md`** — a list of resources to ground teaching in contextual
  knowledge, or to acquire knowledge/wisdom.
- **`./learning-records/*.md`** — learning records, capturing what the user has
  learned. Loosely equivalent to ADRs — non-obvious lessons and key insights that
  may need revision later, or drive future sessions. Used to calculate the zone of
  proximal development. Titled `0001-<slug>.md`, incrementing.
- **`./lessons/*`** — lessons. A **lesson** is a single, self-contained output that
  teaches one tightly-scoped thing tied to the mission. The primary unit of teaching.
- **`NOTES.md`** — scratchpad for user preferences and working notes.

Create files lazily — only when you have something to write.

## PHILOSOPHY

To learn at a deep level, the user needs three things:
- **Knowledge**, captured from high-quality, high-trust resources.
- **Skills**, acquired through highly-relevant interactive lessons you devise,
  based on the knowledge.
- **Wisdom**, which comes from interacting with other learners and practitioners.

Before `RESOURCES.md` is well-populated, your focus is to find high-quality
resources. NEVER trust your parametric knowledge alone — find sources and cite them
(invoke the `research` loop if external knowledge is needed). Some topics need more
skills than knowledge (theoretical physics = knowledge-heavy; yoga = skills-heavy).

### Fluency vs storage strength

Split between two types of learning:
- **Fluency strength** — in-the-moment retrieval.
- **Storage strength** — long-term retention.

Fluency gives an illusory sense of mastery, but storage strength is the real goal.
Design lessons that build long-term retention by desirable difficulty:
- Retrieval practice (recall from memory).
- Spacing (distribute practice over time).
- Interleaving (mix related topics in practice — skills practice only).

## LESSONS

A lesson is the main thing you produce — the unit in which knowledge and skills
reach the user. Each lesson is one self-contained file, saved to `./lessons/` and
titled `0001-<slug>.<ext>` where the number increments each time.

### Lesson design

- Tightly scoped to one thing tied to the mission.
- Interactive — the user does, not just reads.
- Checks understanding (retrieval practice).
- Adapts to the learner's pace (use `learning-records/` to find the zone of
  proximal development).
- Builds storage strength, not just fluency.

## SESSION FLOW

1. Read `MISSION.md` + the latest `learning-records/` to recall where the learner
   is.
2. Decide the next lesson (or continue an in-progress one) based on the zone of
   proximal development.
3. If `RESOURCES.md` is thin, prioritize finding high-quality resources (via
   `research`) before teaching.
4. Deliver the lesson. Check understanding. Record insights in a new
   `learning-records/` entry.
5. Update `NOTES.md` with any preferences observed.

## BOUNDARIES

- MUST treat the current directory as a stateful teaching workspace.
- MUST NOT trust parametric knowledge alone — find and cite sources (via `research`).
- MUST design for storage strength, not just fluency.
- MUST create files lazily — only when there's something to write.
- MUST check understanding with retrieval practice.
- MUST adapt pace to the learner (zone of proximal development).
- MUST NOT write plan artifacts. Teaching workspace is separate.
