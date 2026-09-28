---
name: upfront-dispatch
description: |
  Before the first tool call of a non-trivial user task, classify the task
  across lanes (main loop / free external worker / structured subagent) using
  a decision primitive, then apply a deterministic rule to choose the lane.
  Pairs with the post-hoc dispatcher (which only nudges after reads accumulate)
  by closing the upfront half of the same gap.
  Use when the agent is about to invoke its first tool call for a non-trivial
  task, when the user asks "should I dispatch this?" before any work has
  started, or when in doubt about which lane to pick. Silent by design:
  classify, apply the rule, and proceed without narrating the procedure.
invocation: auto
layer: process
language: en-US
metadata:
  version: "1.0.0"
---

# upfront-dispatch — classify the task before the first tool call

Pairs with the post-hoc dispatcher. The post-hoc dispatcher watches the agent
mid-task and nudges when it should have delegated. This skill runs **before**
the first tool call and decides the lane upfront. Together they bookend the
gap: post-hoc handles the case the agent skipped the upfront, and the upfront
classifier catches the rest before context is wasted.

## Why

Post-hoc nudges work for repeated in-line patterns but cannot recover the
context budget already spent when the agent does 30 reads inline that should
have been delegated to a free worker. Classifying upfront costs one cheap
decision call and preserves context for actual work.

## When (self-trigger)

- The agent received a user message and is about to make its first tool call.
- The task is non-trivial (more than one expected tool call, or any mutation).
- The agent is unsure which lane fits.

Skip:

- Pure Q&A — answer in chat.
- The user already named a lane ("use the free worker", "dispatch an architect",
  "do this inline").
- The post-hoc dispatcher is already evaluating this turn (don't double-judge).

## What it does (overview)

1. Build a compact state string — task description, current working directory,
   observable hints (file globs, command names, role keywords the user
   mentioned). **Never include file contents** (privacy + cost).
2. Call the decision primitive **once** with a fixed batch of typed questions
   (verbatim below). Costs near-zero locally; the fallback path costs fractions
   of a cent.
3. Apply a deterministic rule over the normalized answers to pick a lane.
4. If the rule disagrees with the primitive's own lane pick, log one line and
   follow the rule.
5. Proceed silently — no narration, no post-hoc justification.

## Lanes

| Lane | When |
|---|---|
| `main_loop_direct` | The task needs live host inspection, OR is small enough to handle in the current chat. |
| `free_external_worker` | The task is bulk-text-only corpus work — summarize, classify, OCR, second-opinion on existing text. The free worker does it without local tools. |
| `structured_subagent` | The task needs local edit / grep / worktree tools, OR is irreversible, OR has many dependent ops. Dispatch a subagent; the model slug comes from the role's chain in the routing policy. |
| `inline_justificado` | None of the above; defer to default behavior. |

## Questions for the decision primitive (verbatim, all in ONE call)

The primitive evaluates the following six typed questions in parallel. Pricing
is per input token, not per question — batching is mandatory.

```yaml
needs_local_tools:        # noul
  "The task requires editing files, using local grep/edit/worktree, or
  navigating the project codebase — beyond reading text."
is_live_host_inspection:  # noul
  "The task requires inspecting live local host state: running processes,
  open files, ports, code signatures, active network connections, or user
  files outside the project. Only the main loop has this access."
is_bulk_text_only:        # noul
  "The task is corpus work — summarize, classify, extract, OCR, or
  second-opinion on a text the user already has. No local tools, no mutations."
is_irreversible:          # noul
  "The task mutates files, deletes, pushes, publishes, spends money, touches
  credentials, or otherwise commits state requiring rollback work."
sequential_dependent_ops: # score 1-10
  "How many SEQUENTIAL DEPENDENT tool calls will this task need? (10 =
  fan-out with shared state; 1 = atomic inspection.)"
correct_lane:             # choice
  "Given the policy, which lane fits? Options: main_loop_direct |
  free_external_worker | structured_subagent | inline_justified."
```

The primitive normalizes answers: `noul` clamps to `[0, 1]`, `choice` returns
the selected option plus its probability, `score` returns the integer.

## The rule (deterministic, apply in this strict order)

```text
(A) is_live_host_inspection ≥ 0.70
    → lane = main_loop_direct
    Rationale: only the main loop has live host access; no other lane can.

(B) needs_local_tools < 0.70
    AND is_irreversible < 0.70
    AND is_bulk_text_only ≥ 0.70
    → lane = free_external_worker
    Rationale: text-only corpus work belongs on the free external lane.

(C) needs_local_tools ≥ 0.70
    OR is_irreversible ≥ 0.70
    OR sequential_dependent_ops ≥ 8
    → lane = structured_subagent
    Rationale: complex or mutating work needs isolated context + the routing
    policy's role-specific model chain.

(D) ELSE
    → lane = main_loop_direct
    Rationale: small or ambiguous — safe default.
```

**Threshold 0.70** matches the irreversible-action threshold used elsewhere
in the routing policy. The rule wins over the primitive's own `correct_lane`
pick if they disagree — log one line so the user knows. The rule is the
encoded policy; the primitive is the signal.

## When the lane is `structured_subagent`

Choose the role from the prompt:

| Trigger in prompt | Role |
|---|---|
| "plan first" / "design" / "architect" / "think through" | architect (judgment-tier) |
| external research, lookups, web/docs/API surface | research |
| adversarial review, red-team, second-opinion, audit | review |
| code, fix, refactor, implement, migrate | coder |
| (default) | generalist |

Role chains and slugs come from the canonical routing policy — never invent
slugs. If the user explicitly asked for an isolated branch ("worktree",
"branch", "isolated copy") and the role is `coder` or `architect`, dispatch
in an isolated branch per the `dispatch` skill.

## Procedure

1. Build the state from the prompt (≤3 sentences) + cwd + any observable hints
   (file globs, command names mentioned, role keywords). NEVER include file
   contents.
2. Call the decision primitive **once**. No iteration. If the answer is wrong,
   the cost was negligible — log and move on.
3. Apply the rule above. Note any disagreement with `correct_lane` in one line.
4. Proceed silently when the lane is clear.
5. Skip the classifier entirely for pure Q&A, explicit lane names, or turns
   already covered by the post-hoc dispatcher.

## Worked examples (validated 2026-09-27 against the decision primitive)

The three contrasts in the user's task brief, classified by the rule:

| Prompt | Dominant signal (prob) | Rule lane | Primitive pick | Match |
|---|---|---|---|---|
| "duetexpertd consumes CPU, diagnose" | `is_live_host_inspection` = 1.00 | `main_loop_direct` | `main_loop_direct` | ✓ |
| "summarize the 30 files in this directory and tell me which are critical" | `is_bulk_text_only` = 0.95 | `free_external_worker` | `free_external_worker` | ✓ |
| "implement this RFC in module X, plan first, isolated worktree" | `needs_local_tools` = 1.00, `is_irreversible` = 0.90 | `structured_subagent` | `structured_subagent` | ✓ |

Each case has **one** dominant signal ≥ 0.90 and the rule coincides with
`correct_lane`. Reported cost: ~$0.000077 per call on the cloud fallback
path (free locally).

## Boundaries

- MUST make exactly **one** decision-primitive call per turn that triggers
  this skill. No iteration.
- MUST omit file content from the state (privacy + cost).
- MUST respect the canonical routing policy for any subagent model slug.
  Never invent one.
- MUST be silent when the result is clear.
- MUST log one line when the rule and `correct_lane` disagree; never silently
  override.
- MUST NOT express model or specific tooling in the body of this skill
  (the cross-harness adapter maps behavior to tools).
- MUST NOT modify any other skill, the routing policy, or the post-hoc
  dispatcher config — complement them.
- MUST fail open to `main_loop_direct` when the decision primitive is
  unavailable or returns no usable answer. Treat the absence of the
  classifier the same as `inline_justificado` and proceed — never hang a
  turn on a missing seam.

## Deployment notes (for cross-device portability)

This skill is coupled to **one** runtime seam: a decision-primitive backend
must be reachable on the device. The harness adapter is responsible for
resolving which backend actually answers.

Resolution cascade used by the canonical implementation (degrades down the
list, never throws):

| Tier | Latency | Cost / call | Calibrated? | Practical role |
|---|---|---|---|---|
| Local server (Apache 2.0 model, self-hosted) | ~30-100ms | $0 | yes | optimization — nice when present |
| **Free fallback API (already-authorized host)** | **~1.6s** | **~$0.00001** | **no** | **the de facto primary tier** |
| Commercial typed-decision API (key-gated) | ~200-300ms | ~$0.00002 | claimed | optional upgrade if calibration matters |
| Heuristic fallback (no credentials) | <1ms | $0 | no | last-resort, treat output as advisory |

**Practical stance (revised 2026-09-27):** the deterministic rule above does
the actual classification; the primitive only supplies the signal that drives
it. With six batched noul/choice/score questions, the rule is robust to
moderate calibration drift — the threshold 0.70 was chosen to absorb it.
That makes the **free fallback API tier the effective primary tier** on any
device with the API key (which is the most common cross-device case):
~$0.00001 per call, ~1.6s latency, acceptable for an upfront gate that
fires once per task. Local server is an optimization to reach for on a
workstation, never a prerequisite. Heuristic fallback and missing-seam
fail-open exist for genuinely offline or restricted deployments; on those,
the MUST fail-open rule above takes over and the lane becomes
`main_loop_direct`.

## Out of scope

- **Automatic triggering**: leaving the trigger to the agent's judgment is
  part of the design. Automating requires a new layer between the user
  message and the agent loop, which belongs to the harness adapter, not this
  skill.
- **Panel adversarial opinions**: the post-classification panel belongs in
  the routing policy, not here.
- **Post-hoc behavior**: belong to the post-hoc dispatcher, not this skill.
- **Calibrating the 0.70 threshold per backend**: the post-classification
  calibration regime lives in the routing policy, not this skill. Adjust
  there, not here.
- **Picking a specific backend**: the cross-harness adapter resolves the
  seam; this skill never names one.
