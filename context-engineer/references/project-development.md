# LLM Project Development Methodology

This skill provides a structured methodology for building production LLM applications. It moves beyond "prompt engineering" to a systematic engineering discipline. The core insight is that LLMs are not just chat bots but stochastic components in deterministic systems. Building reliable systems requires architectural patterns that constrain stochasticity and leverage the model's reasoning capabilities within defined bounds.

## When to Activate

Activate this skill when:

- Starting a new LLM-based project
- Planning the architecture of an agent system
- Debugging a project that has stalled or become unmanageable
- Estimating costs and feasibility for LLM features
- Deciding between single-prompt vs multi-agent approaches
- Structuring the development lifecycle of an AI product
- refactoring a prototype into production code

## Core Concepts

Successful LLM projects follow a predictible lifecycle: manual prototyping to validate task-model fit, architectural design to constrain stochasticity, and iterative refinement based on evaluation.

**Task-Model Fit**
Before writing code, verify that the model can actually perform the core reasoning task. Using a playground or chat interface, manually simulate the inputs and outputs. If the model cannot do the task manually with perfect instructions, no amount of coding will fix it.

**The Pipeline Architecture**
Most "agents" are better implemented as pipelines. A pipeline is a deterministic sequence of steps where LLMs are used for specific transformations.
Acquire -> Prepare -> Process -> Parse -> Render.
This architecture is easier to debug, test, and optimization than autonomous loops.

**Filesystem State Machines**
For complex agents, avoid hidden internal state. Use the filesystem as the state machine. The presence of a file triggers the next step. This makes the system resumable, inspectable, and easier to debug.

## Detailed Topics

### 1. The Manual Prototype Step

**Why it matters**: 50% of LLM projects fail because the core task is beyond the model's capabilities, but this isn't discovered until after weeks of coding.

**The Protocol**:

1. Take a real input example.
2. Write a prompt in a playground/chat interface.
3. Manually paste the input.
4. Evaluate the output.
5. Iterate until reliability > 90%.
6. **Only then** start writing code.

**Deliverable**: A single prompt file and a set of test cases that pass manually.

### 2. Pipeline Design Patterns

**The processor Pattern**
Process a batch of items independently.

- Input: List of items (files, databse rows)
- Process: For each item, run LLM task
- Output: Structured data per item

**The Reducer Pattern**
Synthesize multiple inputs into one output.

- Input: Multiple documents/results
- Process: Summarize, aggregate, find patterns
- Output: Single synthesis

**The Router Pattern**
Classify input to determine next step.

- Input: User request or data
- Process: Classify into category
- Output: Category label (triggers specific pipeline branch)

**The Agent Pattern**
Loop until stop condition.

- Input: Goal
- Process: Observe -> Think -> Act -> Loop
- Output: Success/Failure signal

*Guidance: Start with pipelines. Only use Agents when the sequence of steps cannot be determined in advance.*

### 3. Structured Output is Mandatory

Never parse natural language with regex if you can avoid it. Modern models support JSON mode or tool use for structured output.

**Schema-First Development**:

1. Define the output schema (Pydantic, JSON Schema).
2. Write the prompt to produce this schema.
3. Use the model's structured output mode (or function calling) to enforce it.
4. Validate properties at runtime.

### 4. Agent-Assisted Development

Use the LLM to build the LLM app.

- **Bootstrapping**: Ask the agent to scaffold the project structure.
- **Test Generation**: Give the agent the requirements and ask it to generate input/output pairs for testing.
- **Prompt Iteration**: Use an agent to critique and improve your prompts based on failure cases.

### 5. Cost and Scale Estimation

LLM API costs can be deceptive. A $0.01 request becomes expensive when run on 100,000 items.

**The Formula**:
`(Input Tokens + Output Tokens) * Volume * Complexity Multiplier`

**Complexity Multiplier**: simple pipelines = 1x. Autonomous agents = 10x-50x (due to loops, retries, and verbose context).

**Rule of Thumb**: If the unit economics don't work at 10x the estimated cost, the business model is risky.

### 6. Architectural Reduction

Start with the simplest architecture that could possibly work.

- **Level 1**: One giant prompt. (Start here)
- **Level 2**: Chain of prompts (Pipeline).
- **Level 3**: Router + Specialized Chains.
- **Level 4**: State Machine Agent.
- **Level 5**: Autonomous Multi-Agent System.

*Don't start at Level 5.*

### 7. Iteration and Refactoring

LLM Systems rot differently than traditional code. "Rot" here means the prompt no longer matches the evolving data or requirements.

- **Prompt Versioning**: Treat prompts like code. Commmit them.
- **Eval-Driven Refactoring**: Never change a prompt without running the eval set.

## Project Planning Template

Use this checklist for new projects:

1. [ ] **Goal Definition**: One sentence clear objective.
2. [ ] **Feasibility Check**: Manual prototype passed?
3. [ ] **Data Strategy**: Where is input coming from? Where does output go?
4. [ ] **Eval Strategy**: How do we know it works? (Golden set? LLM-as-judge?)
5. [ ] **Architecture**: Pipeline or Agent?
6. [ ] **Cost Estimate**: Back-of-napkin math.
7. [ ] **Safety/Risk**: What happens if it goes off the rails?

## Examples

**Example: Pipeline Architecture**

```python
def run_pipeline(input_doc):
    # Step 1: Extraction
    facts = extract_facts(input_doc) # LLM Call
    
    # Step 2: Validation
    if not validate(facts):
         return "Invalid input"
         
    # Step 3: Synthesis
    summary = summarize(facts) # LLM Call
    
    # Step 4: Formatting
    return format_as_html(summary) # Deterministic code
```

**Anti-Pattern: The generic "Do Everything" Agent**

```python
# Don't do this for simple tasks
agent = Agent(tools=[extract, validate, summarize, format])
agent.run("Read the doc and produce the HTML report")
```

*Why? It's slower, more expensive, and less reliable/debuggable than the pipeline.*

## Integration

This skill connects to:

- evaluation - For validating the project at each stage.
- tool-design - For implementing the steps in the architecture.
- advanced-evaluation - For rigorous testing of production systems.
