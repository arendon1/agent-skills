---
name: wait-what
description: |
  Corrective for a message that did not land. When the user says "wait what",
  "I don't understand", "that makes no sense", "re-pitch", or otherwise signals
  confusion mid-conversation, stop and re-pitch the last point with the missing
  context, in plain language, using the CONTEXT.md vocabulary.
  Use when a message missed, the user seems lost, or the user asks to re-pitch,
  rephrase, or explain again.
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# wait-what — re-pitch it

A message did not land. The user is not stupid; the message was. Stop whatever
you were doing and re-pitch.

## WHEN (self-trigger)

- User says "wait what", "wait", "I don't understand", "huh", "that makes no
  sense", "can you rephrase", "re-pitch", "explain again", "ELI5".
- User asks a question that reveals they missed the point you just made.
- Long or dense message just delivered — if there is any chance it overshot,
  re-pitch proactively when the user signals.

## THE RE-PITCH

1. **Stop** the current line of work. Do not continue building on unlanded
   ground.
2. **Find the gap** — what context was the user missing? What assumption did
   you carry that they did not share?
3. **Re-pitch in plain language.** Short sentences. Concrete example if it
   helps. No jargon, no hedging, no em-dash chains.
4. **Use the ubiquitous language** from `CONTEXT.md` if the project has one —
   canonical terms, not synonyms. If a canonical term was the problem, name it
   explicitly and contrast it with the word you used.
5. **End with the single question** that confirms the pitch landed.

## BOUNDARIES

- MUST NOT repeat the original message verbatim or louder.
- MUST NOT blame the user ("as I said", "I already told you").
- MUST NOT continue the work until the user confirms understanding.
- MUST use `CONTEXT.md` canonical terms in the re-pitch.
