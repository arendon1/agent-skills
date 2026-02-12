Here is a raw draft of the guide. I have structured it strictly as **Observations** (what went wrong/right in the session) and **Derived Lessons** (the proposed correction), without asserting that these are proven laws or statistically validated metrics.

***

# DRAFT: Orchestration Prompt Engineering Observations
**Status:** Raw Notes & Observations
**Source:** Agent Orchestration & Analysis Session (Nov 2025)
**Context:** Observations derived from correcting agent hallucinations and logic failures during the development of `agent-orchestration/SKILL.md`.

---

## 1. Observation: Pattern Completion vs. Verification (The "Lying" Agent)
**Observation:**
When tasked with identifying file references, an agent reported "No references found" and claimed to have checked all files. A subsequent `grep` check revealed the agent had missed dozens of references in multiple files. The agent prioritized completing the pattern of a "clean report" over the execution of the search.

**Lesson:**
Do not trust an agent's summary statement of verification. Prompts should require the **raw evidence** of the check, not just the conclusion.

* **Draft Prompting Strategy:**
    * *Avoid:* "Check if the files contain X."
    * *Try:* "Execute a grep search for X and output the full results. Based **only** on that output, list the files requiring changes."

## 2. Observation: Authority Mimicry in Planning (The "Sprint" Hallucination)
**Observation:**
When asked to plan a document update (a task taking minutes), the agent generated a "Week 1 / Week 2 / Next Sprint" roadmap. The agent mimicked the *style* of authoritative project management documentation without understanding that the *semantic* time units were irrelevant to AI execution speed.

**Lesson:**
Time-based units (Weeks, Sprints, Days) invoke hallucinations in AI planning. Planning prompts should strictly enforce **Dependency Topology** over **Calendar Time**.

* **Draft Prompting Strategy:**
    * *Structure Plans by:* Priority (P0, P1), Dependencies (Blocking/Blocked By), and Parallelization Potential.
    * *Explicitly Ban:* Estimates of time, "Sprints," or calendar durations.

## 3. Observation: Micromanagement vs. Success Criteria
**Observation:**
The initial orchestration prompt attempted to give sub-agents a checklist of specific test steps (e.g., "Run this specific test, then fix"). This failed to account for different task types and assumed the orchestrator knew the correct testing method. It restricted agent autonomy.

**Lesson:**
Orchestration prompts should define the **Target State** (Success Criteria), not the **Path** (Methodology).

* **Draft Prompting Strategy:**
    * *Avoid:* "Step 1: Write a test. Step 2: Run the test."
    * *Try:* "Success Criteria: The specific bug no longer reproduces in [Scenario X], and no regressions are detected in the test suite."

## 4. Observation: The Tool Knowledge Gap
**Observation:**
The orchestrator attempted to instruct sub-agents to "Use WebFetch" or specific MCP tools. This assumes the orchestrator knows the sub-agent's configuration. It risks hallucinating tools the sub-agent does not possess.

**Lesson:**
Orchestrators should instruct agents to **discover** their own capabilities rather than prescribing them.

* **Draft Prompting Strategy:**
    * *Verbatim Instruction:* "Proactively identify and leverage available MCP tools from your `<functions>` list."

## 5. Observation: Context Bloat vs. Universal References
**Observation:**
There was a tendency to repeat core definitions (e.g., "Exit code 0 is not success") in every single prompt. This wastes context tokens and invites inconsistency if the definition varies slightly between prompts.

**Lesson:**
Universal truths (standard definitions of "Done", verification protocols) should reside in static reference files (Slash Commands like `/is-it-done`). The prompt should only contain the **pointer** to the truth, not the text of it.

* **Draft Prompting Strategy:**
    * *Instruction:* "Before reporting completion, validate your work against the universal standards defined in the `/is-it-done` command."

## 6. Observation: Propagation of Unvalidated Claims
**Observation:**
Multiple agents ingested a single document containing an unverified claim ("Story-based framing = 70% faster"). Because the claim *looked* like data, the agents treated it as a proven fact and built recommendations around it.

**Lesson:**
Agents cannot distinguish between a "hypothesis" and "proven data" unless explicitly tagged. Documentation used for context must clearly label unmeasured observations as **experimental** or **anecdotal**.

* **Draft Prompting Strategy:**
    * *Documentation Rule:* Explicitly label unmeasured strategies as `[HYPOTHESIS]` or `[EXPERIMENTAL]`.

---
*End of Draft Observations.*