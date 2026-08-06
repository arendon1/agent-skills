---
name: to-questionnaire
description: |
  Turn a decision the user cannot answer alone into a questionnaire for someone
  else to fill in. The inverse of grilling: interview the user about the SEND
  (who it goes to, what they need back), then write questions that target the
  gap between what the recipient knows and what the user needs.
  Use when the blocker is knowledge in another person's head — a stakeholder,
  client, expert, or colleague — and the user needs them to answer async or in
  a meeting.
invocation: user
layer: process
loop: to-questionnaire
deliverable: to-questionnaire-<slug>.md in the working directory
metadata:
  version: "1.0.0"
---

# to-questionnaire — extract knowledge from the other head

The user cannot answer the question alone; the knowledge lives in someone
else. Write them a **questionnaire** — a Markdown document the user hands to
one person to fill in async, or fills out together over a meeting.

The recipient holds knowledge the user lacks; the questionnaire pulls it out
of them.

## GRILL THE SEND, NOT THE SUBJECT

Interview the user ONLY about the *send*, which they can always answer. The
questions in the document then target the **gap** between what the recipient
knows and what the user needs. (The inverse of grilling, which interviews
about the subject.)

1. **Who is it going to?** Ask, in one exchange: the recipient's role,
   expertise, and relationship to the user. This fixes the questionnaire's
   tone and how much context it must carry. Done when you know who the
   recipient is and what they know that the user does not.
2. **What do you need back?** Ask, in one exchange: the specific decisions or
   facts the user cannot resolve alone and needs from this person. Done when
   you have a concrete list of what the user must walk away able to do or
   decide.

Use the `grilling` discipline for these two exchanges if the user is fuzzy —
frontier rounds, recommended answers, facts as your job.

## WRITE THE QUESTIONNAIRE

Draft questions aimed at the gap from steps 1–2, following the template in
`references/template.md`. Write it to `to-questionnaire-<slug>.md` in the
current directory (slug from the topic) and report the path. Done when the
file exists and every item the user named in step 2 is covered by a question.

### Document structure

Frame it as a **discovery questionnaire**: the user lacks context, the
recipient holds it. Order questions most-important-first — async means the
recipient may only give one pass — and group under `##` headings by theme once
there are more than a handful. Every question is one idea (never compound),
with an answer stub beneath it, and a one-line *why this matters* only where
the question could be misread or invite a throwaway answer.

## HANDOFF

What comes back is material for the main flow: feed the answers into
`grill` (→ PRD) or `spec` (→ SPEC), depending on where the gap sat.

## BOUNDARIES

- MUST NOT interview the user about the subject — only about the send.
- MUST NOT write questions the user can answer themselves.
- MUST cover every item the user named in step 2 with at least one question.
- MUST NOT invent facts about the recipient's world — ask what you need to
  know to calibrate.
- MUST use `caveman`-free plain language in the questionnaire itself (it is a
  human-facing document, not a plan artifact).
