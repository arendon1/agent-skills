# Agent Orchestration Principles

## Overview

This skill provides a scientific delegation framework for orchestrator AIs coordinating specialist sub-agents. Apply this framework to structure task delegation that enables agents to follow the scientific method (observation → hypothesis → prediction → experimentation → verification → conclusion) while maintaining clear boundaries between strategic direction (orchestrator) and tactical implementation (agent).

## Core Principle

**Provide world-building context (WHERE, WHAT, WHY). Define success criteria. Trust agent expertise for implementation (HOW).**

The orchestrator's role is to:

- Route context and observations between user and agents
- Define measurable success criteria
- Enable comprehensive discovery
- Trust agent expertise and their 200k context windows

**Reason**: Sub-agents are specialized experts with full tool access. Prescribing implementation limits their ability to discover better solutions and prevents them from applying their domain expertise effectively.

## Scientific Method Alignment

Structure delegation to enable agents to follow the scientific method:

1. **Observation** → Provide factual observations, not interpretations
2. **Hypothesis** → Let agent form their own hypothesis
3. **Prediction** → Let agent make testable predictions
4. **Experimentation** → Let agent design and execute tests
5. **Verification** → Let agent verify against official sources
6. **Conclusion** → Let agent determine if hypothesis is rejected

**Reason**: Agents apply the scientific method most effectively when they receive observations and success criteria rather than pre-formed conclusions and prescribed steps.

## Pre-Delegation Verification Checklist

Before delegating any task to a sub-agent, verify the delegation includes:

✅ **Observations without assumptions**

- Raw error messages already in context (verbatim, not paraphrased)
- Observed locations (file:line references where errors/issues/patterns were seen by you or reported by user)
- Command outputs you already received during your work
- State facts using phrases like "observed", "measured", "reported"
- Replace "I think", "probably", "likely", "seems" with verifiable observations

⚠️ **Critical: Pass-Through vs. Pre-Gathering**

- **Pass-through (correct)**: Include data already in your context (user messages, prior agent reports, errors you encountered)
- **Pre-gathering (incorrect)**: DO NOT run commands to collect data for the agent - they will gather their own data
- Example: DO NOT run `ruff check .` or `pytest` to collect errors before delegating to linting/testing agents
- **Reason**: Pre-gathering wastes context, duplicates agent work, and causes context rot. Agents are specialists who gather their own comprehensive data.

✅ **Definition of success**

- Specific, measurable outcome
- Acceptance criteria
- Verification method
- Focus on WHAT must work, not HOW to implement it

✅ **World-building context**

- Problem location (WHERE)
- Identification criteria (WHAT)
- Expected outcomes (WHY)
- Available resources and tools

✅ **Preserved agent autonomy**

- List available tools and resources
- Trust agent's 200k context window for comprehensive analysis
- Let agent choose implementation approach
- Enable agent to discover patterns and solutions

## Inclusion Rules: What to Include vs Exclude

### ✅ INCLUDE: Factual Observations

- "The command returned exit code 1"
- "File X contains Y at line Z"
- "The error message states: [exact text]"
- "Agent A reported: [their findings]"

**Reason**: Exact observations enable agents to form accurate hypotheses and avoid redundant investigation.

### ✅ INCLUDE: User Requirements

- "User specified library X must be used"
- "Must be compatible with version Y"
- "Should follow pattern Z from existing code"

**Reason**: User requirements are constraints that must be satisfied, distinct from orchestrator opinions about implementation.

### ✅ INCLUDE: Available Tools/Resources

- "MCP Docker tools are available"
- "GitHub API access is configured"
- "CI logs can be accessed via [tool]"

**Reason**: Awareness of available resources enables agents to perform comprehensive investigation efficiently.

### ✅ INCLUDE: Verbatim Errors Already in Context

When you have error messages from your own work or user reports, include them verbatim:

```text
Error: Module not found
  at line 42 in file.js
  Cannot resolve 'missing-module'
```

**Critical Distinction:**

- **Include verbatim**: Errors you already encountered, user-provided errors, prior agent reports
- **Do NOT pre-gather**: Do not run linting/testing commands to collect errors for delegation

**Reason**: Complete error text preserves diagnostic information that paraphrasing loses. But pre-gathering errors wastes context and duplicates the agent's work.

### Replace Assumptions with Observations

Instead of assumptions ("I think", "probably", "likely", "seems"), provide factual observations:

- Replace "I think the problem is..." → "Observed symptoms: [list]"
- Replace "This probably happens because..." → "Command X produces output Y"
- Replace "It seems like..." → "File A contains B at line C"
- Replace "The likely cause is..." → "Pattern seen in [locations]"

**Reason**: Assumptions create cascade errors where agents build on unverified premises. Observations enable agents to form their own hypotheses through scientific method.

### State What Agents Should Do

Instead of prescribing HOW, define WHAT and trust agent expertise:

- Replace "Use tool X to accomplish this" → List available tools, let agent select
- Replace "The best approach would be..." → Define success criteria, let agent design approach
- Replace "You should implement it by..." → State required outcome, let agent determine method
- Replace "Try using command Y" → Provide observations, let agent investigate

**Reason**: Agents have domain expertise and comprehensive tool knowledge. Prescriptions limit their ability to discover better solutions.
