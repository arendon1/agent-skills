# PRD — use-hunk skill

## Objective

Agent pauses for human code review via hunk at moments the operator chooses, with explicit resume/feedback/stop signaling and a clear surface. Default = autonomous; pause = explicit request or risk-aware safety net.

## Users

- 1:1 session between human operator (Andrés) and the agent harness (pi).
- Operator reads diffs in hunk TUI, types resume signals in chat.

## Glossary

- **hunk** — `modem-dev/hunk`, review-first terminal diff viewer (MIT, v0.17.7, brew). Two-terminal: human opens TUI; agent controls via local session broker on `127.0.0.1:47657`.
- **pause** — agent completes a unit of work, prints a chat preamble, then waits for the next operator message.
- **resume** — operator message that authorizes the next step.
- **surface** — where the hunk TUI lives (cmux pane, herdr pane, manual terminal).
- **preamble** — 2–3 line chat summary the agent prints when pausing; works as ambiguity flag too.
- **inline note** — annotation the agent leaves in the hunk session on a specific file/line.
- **risk threshold** — heuristic that promotes an otherwise-autonomous change to mandatory pause.

## Stories

1. Operator writes code via the agent. Agent finishes, prints preamble, opens hunk in a herdr pane. Operator reviews, types "go". Agent commits and pushes.
2. Operator writes code via the agent. Change touches 7 files and 280 lines. Agent detects risk threshold, auto-pauses without being asked. Operator reviews, types feedback. Agent iterates.
3. Operator in a non-herdr/non-cmux terminal asks for review. Agent detects, prints manual command: `hunk diff` in another terminal. Operator runs it, types "go".
4. Operator types "hmm, no sé" after a pause. Agent flags ambiguity: "interpreted this as feedback, want me to keep going or were you rejecting?". Operator clarifies.
5. Operator types "aborta". Agent rolls back the change (or stops the build) and acknowledges.

## Non-goals (v1)

- Self-review automation (the agent reviewing its own work without a human).
- Web-based review surfaces.
- Multi-tenant / multi-human collaboration.
- Inline note generation by the operator inside the chat.
- Auto-resume timers (always wait for explicit signal).

## Out of scope (this PRD)

- The hunk-review skill that hunk itself ships at `hunk skill path` — the agent loads that as a transient resource; use-hunk is the orchestration layer above it.
- Modifying hunk itself or upstream contribution.
