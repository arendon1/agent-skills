# BDI Mental State Modeling

Belief-Desire-Intention (BDI) is a cognitive architecture for modeling rational agents. It provides a structured way to reason about an agent's internal state, moving beyond simple input-output mapping to agents that have "mental models" of their world, goals, and plans. Using BDI terminology in system prompts significantly improves an agent's ability to maintain coherent behavior over long interactions.

## When to Activate

Activate this skill when:

- Designing complex autonomous agents that need to plan and adapt
- Debugging agents that get "confused" or lose track of goals
- Implementing agents that need to explain their reasoning (Explainable AI)
- Creating agents that must model the user's mental state (Theory of Mind)
- writing system prompts for high-reasoning capability models

## Core Concepts

The BDI model separates mental state into three components:

- **Beliefs**: Information the agent holds to be true about the world (World Model).
- **Desires**: States of affairs the agent wants to bring about (Goals).
- **Intentions**: Desires the agent has committed to achieving (Plans/Actions).

By explicitly tracking these states, an agent can distinguish between "what I know," "what I want," and "what I am doing."

### The Mental Reality Architecture

**Beliefs (World State)**

- **Static Beliefs**: Rules, definitions, immutable facts.
- **Dynamic Beliefs**: Current observations, variable state.
- *Prompting Pattern*: "Based on the file X, I believe the current system status is Y."

**Desires (Goal Space)**

- **Ideally**: "Optimize for maximum performance."
- **Practically**: "Ensure latency < 200ms."
- *Prompting Pattern*: "My goal is to achieve X, while respecting constraint Y."

**Intentions (Commitment)**

- The subset of desires the agent is actively working on.
- *Prompting Pattern*: "I am currently executing the plan to refactor module Z."

### The Cognitive Chain Pattern

For complex reasoning, force the agent to traverse the BDI chain explicitly.

1. **Perception**: "I see output X from tool Y."
2. **Belief Update**: "This changes my belief about Z from A to B."
3. **Desire Check**: "Does this align with my goal G?"
4. **Intention Formation**: "Therefore, I intend to execute action A next."

### World State Grounding

Agents hallucinate when their beliefs are not grounded in evidence. BDI enforces grounding.

- **Rule**: Every belief must trace back to an observation (tool output, user message, static context).
- **Self-Correction**: "I hold belief B, but I cannot find the source. I must verify B."

### Goal-Directed Planning

Instead of "following instructions," BDI agents "pursue goals."

- **Hierarchical Goals**: Break high-level desires into sub-goals.
- **Adaptive Planning**: If Intention A fails, the Desire remains. The agent forms a new Intention (Plan B) to satisfy the same Desire.

*This makes agents robust to failure. A script fails; a BDI agent retries with a different approach.*

## Detailed Topics

### 1. Notation for System Prompts

Use explicit sections in your system prompt or agent scratchpad:

```markdown
# Mental State
## Current Beliefs
- The database is currently locked (Source: error log).
- The user allows force-unlocking (Source: user preference file).

## Active Goals (Desires)
1. Restore database access (High Priority).
2. Preserve data integrity (Critical Constraint).

## Current Plan (Intentions)
1. Attempt safe unlock.
2. If fail, request manual intervention.
```

### 2. Justification and Explainability

BDI provides a natural framework for explainability.

- User: "Why did you do that?"
- Agent: "I performed Action A (Intention) because I believed B (Belief) and I wanted to achieve G (Desire)."

### 3. Integration with Memory

- **Beliefs** -> Long-term Memory / Knowledge Graph.
- **Intentions** -> Working Memory / Task List.
- **Desires** -> System Prompt / Mission Statement.

### 4. BDI in Multi-Agent Systems

- **Shared Beliefs**: Common Ground.
- **Conflicting Desires**: Negotiation required.
- **Joint Intentions**: Cooperative plans.

## Practical Guidance

### Writing BDI Prompts

Don't just say "You are a helpful assistant." Say:
"You are a rational agent. Maintain a model of the user's project (Beliefs). Your objective is to refactor the code (Desire). You will form plans (Intentions) to achieve this, adapting to errors as they occur."

### Debugging with BDI

When an agent fails, ask:

1. **Belief Error**: Did it see the wrong thing? (Hallucination/Observation failure)
2. **Desire Error**: Did it misunderstand the goal? (Alignment failure)
3. **Intention Error**: Did it choose a bad plan for a correct goal? (Reasoning failure)

## Integration

This skill connects to:

- evaluation - Assessing the rationality of agent decisions.
- memory-systems - Storing beliefs.
- multi-agent-patterns - Coordinating intentions between agents.
