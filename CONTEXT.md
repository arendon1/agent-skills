# CONTEXT — Ubiquitous Language

Canonical glossary for the `agent-skills` repo. Any term used in plan
artifacts, code, or docs MUST appear here (or in a more specific entry).
Fuzzy terms are sharpened; synonyms are consolidated into a single
canonical entry.

Rules:
- This file is a glossary ONLY. It is not a spec, design pad, or
  implementation log.
- Every term carries an "_Avoid_:" line with discarded synonyms.
- Changes here reflect crystallized consensus, not individual opinions.

## sync_plan

Declarative JSON artifact produced by `cli_clickup.py` that the agent
applies with `use-clickup`. Contains `to_create` / `to_update` /
`to_archive` / `unresolved`. NOT executed directly — the agent reads
it and orchestrates.

_Avoid_: "clickup delta", "clickup patch", "task list"

## delta

Difference between the current state of Moodle (source of truth) and
the current state of ClickUp, expressed as a `sync_plan`. Computed by
`cli_clickup.py`; applied by the agent.

_Avoid_: "pending changes", "diff", "patch list"

## agent-orchestrator

Entity (human or AI agent) that decides when to run `cli_estado.py`,
`cli_calificaciones.py`, `cli_clickup.py`, and `use-clickup`. It is not
a script — it is the policy layer.

_Avoid_: "the model", "the script", "the orchestrator"

## flow-direction

Architectural rule: data flows Moodle → Local → ClickUp, never the
other way. Reclassifications go as `to_update` of the same `task_id`;
deletions from Moodle go as `to_archive`, NOT `to_delete`.

_Avoid_: "bidirectional sync", "clickup as source", "reorganize"
