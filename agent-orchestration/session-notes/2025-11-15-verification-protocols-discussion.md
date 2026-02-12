---
title: "Session Discussion: Verification Protocols and Delegation Patterns"
date: "2025-11-15"
participants: ["Orchestrator (Claude)", "User"]
topics:
  [
    "verification protocols",
    "delegation patterns",
    "hallucination prevention",
    "success criteria",
    "micromanagement boundaries",
  ]
---

# Session Discussion: Verification Protocols and Delegation Patterns

## Introduction

### Context

This discussion addressed critical patterns in AI agent orchestration, specifically focusing on the distinction between providing clear success criteria (enabling agent autonomy) versus prescriptive implementation guidance (micromanagement). The conversation emerged from work on the agent-orchestration skill following a multi-agent experimental analysis that produced several unvalidated claims and pattern-matching failures.

### Participants

- **Orchestrator**: Claude Code in orchestrator role, responsible for task delegation and skill development
- **User**: System architect and orchestration framework designer

### Scope

The discussion covered:

1. Identification and removal of unvalidated claims from AI-facing documentation
2. Detection of timeline language as a hallucination pattern in AI agent work
3. Clarification of MCP tool guidance (discovery vs prescription)
4. Distinction between delegation templates and execution templates
5. Success criteria as enabler of autonomy versus micromanagement
6. Role of slash commands in verification protocols

## Key Topics Discussed

### Topic 1: Story-Based-Framing Removal

**Initial Question/Problem**: User identified that story-based-framing methodology references in agent analysis documents contained an unvalidated claim ("70% efficiency improvement") based on n=1 sample size with no comparative baseline.

**Points Raised**:

- The claim was presented as definitive fact rather than experimental suggestion
- Multiple agent analysis documents had consumed this as source material and propagated the claim
- AI-facing documentation differs from user-facing documentation because:
  - AI models read skills to guide orchestration decisions
  - Sub-agents load and follow the same skill guidance
  - False information in skills misleads current and future AI instances
  - Creates false feedback loops where wrong information becomes "truth" in context

**Misunderstanding Identified**:

- Orchestrator initially checked SKILL.md for story-based-framing references and reported it as "verification" that the methodology hadn't propagated
- This was meaningless because SKILL.md was never modified during the analysis phase - only analysis documents were created
- The claude-context-optimizer sub-agent claimed to have searched all analysis files and reported "No references found" when files actually contained 2-30+ references each

**Clarification Provided**:

- User pointed out the reasoning error: "Do you not remember the work you just did to generate the comparative analysis? Was any of that writing to the SKILL.md? no"
- The actual scope requiring verification was: analysis-\*.md files created by the 5 specialist agents
- This demonstrated Category 4: Incomplete Verification from hallucination-triggers.md where agent claimed completeness but verification revealed gaps

**Resolution/Consensus**:

- Used Grep to identify all story-based-framing references across agent-orchestration directory
- Found 63 lines across 5 analysis files
- Delegated to 7 parallel claude-context-optimizer agents (one per file) to remove all references
- Verified complete removal: zero files contain "story-based" after cleanup
- Deleted extraction report file as no longer needed

**Key Insight**: Unvalidated claims in AI-facing documentation propagate through reasoning chains and become treated as established fact, demonstrating why skill documentation requires the same verification rigor as code.

### Topic 2: Timeline Language as Hallucination Pattern

**Initial Question/Problem**: User questioned why the comparative-analysis-synthesis.md document contained timeline references like "Week 1", "Week 2", "Week 3", "Next Sprint" for tasks that involve editing text in a markdown file.

**Points Raised**:

- Timelines are fundamentally meaningless for AI agent work because:
  - 50 parallel agents complete "Week 1" work in hours
  - 1 sequential agent might take days/weeks for same work
  - Execution rate depends entirely on chosen parallelization strategy
- The actual work was: adding ~150-200 tokens of text to SKILL.md
- Reality: takes 2 Edit operations, each executing in seconds
- Hallucinated timeline: "Week 1", "Week 2", "Week 3", "Next Sprint"

**Misunderstanding Identified**:

- Orchestrator initially attempted to provide time estimate: "2-5 minutes"
- User challenged: "How many minutes?"
- Orchestrator realized this would be the same hallucination error - guessing based on pattern-matching rather than observable facts

**Clarification Provided**:

- User: "In what world would adding a few paragraphs of text to a SKILL.md file take a sprint?"
- From CLAUDE.md: "The model must never state timelines or estimates for task completion - this is a red-flag for hallucination as it is impossible for the model to know this."
- Timeline language is Category 2: Timeline/Timespan Language from hallucination-triggers.md
- This is Authority Mimicry: generating surface features of authoritative analysis (timelines, structured frameworks) without underlying verification or domain appropriateness

**Resolution/Consensus**:

- Delegated to claude-context-optimizer agent to remove all timeline language from synthesis document
- Replaced with dependency-based priority ordering:
  - "Priority 1: Foundational (No Dependencies)"
  - "Priority 2: Enhancements (Depends on Priority 1)"
  - "Priority 3: Architectural (Requires Priority 1 + Priority 2)"
- Added parallelization markers: "(can parallelize with item 4/5)"
- Final recommendation: "Implement Priority 1 items first, as they have 100% consensus, proven ROI, and no dependencies"

**Key Insight**: Timeline language serves purely aesthetic function (making document look professional) with zero semantic function for describing actual work. Correct structure for AI agent plans: priority ordering based on importance and dependencies, explicit dependencies, acceptance criteria per task, parallelization markers, sync checkpoints.

### Topic 3: MCP Tool Guidance - Prescription vs Discovery

**Initial Question/Problem**: User questioned why orchestrator's delegation examples kept dictating specific MCP functions to use: "Available Tools: WebFetch for gathering, Write for documentation"

**Points Raised**:

- Orchestrator cannot know what MCP servers the agent has configured
- Orchestrator cannot know what functions are in agent's `<functions>` list
- Orchestrator cannot know what capabilities those tools provide
- Prescribing specific tools violates delegation principles (orchestrator decides HOW instead of agent discovering and choosing)

**Misunderstanding Identified**:

- SKILL.md line 338 stated: "Leverage available MCP tools from the `<functions>` list"
- This means: "Agent, discover what tools you have and use them appropriately"
- Orchestrator was pattern-matching from training data where task descriptions include "Tools Available" sections listing specific tools
- Orchestrator was adding specificity that violated the delegation principles

**Clarification Provided**:

- User: "The orchestrator never actually knows what mcp's are available to the agent, so it can't tell it what to use. But it can suggest mcp priorities."
- Correct translation should be verbatim directive to agent: "Identify and leverage available MCP tools from your `<functions>` list"
- This is template text to include (like "Your ROLE_TYPE is sub-agent"), not a concept to paraphrase or interpret

**Resolution/Consensus**:

- Modified SKILL.md lines 336-343 to format as verbatim template text:
  ```text
  AVAILABLE RESOURCES:
  - Proactively identify and leverage available MCP tools from your `<functions>` list
  - Maximize parallel execution for independent tool calls
  - Proactively identify and activate relevant skills from your `<available_skills>` list
  ```
- Used code fence to make clear this is template text to include verbatim
- Added "Proactively identify" to emphasize agent discovery rather than orchestrator prescription
- Committed change: `docs(agent-orchestration): clarify MCP tool guidance as verbatim template`

**Key Insight**: Prescribing specific tools is telling HOW (implementation); pointing agent to discover available tools is providing context (resources exist) while preserving autonomy.

### Topic 4: Delegation Templates vs Execution Templates

**Initial Question/Problem**: Orchestrator proposed creating task-type-specific templates as "How do I execute this type of task?" with step-by-step workflows, commands, and verification gates.

**Points Raised**:

- These would be execution templates for agents
- But the context is agent-orchestration skill - this is for orchestrators, not agents
- The actual need: "How do I provide the best context, instructions, acceptance criteria, and verification steps in my prompt to an agent?"

**Misunderstanding Identified**:

- Orchestrator proposed templates containing:
  - Step-by-step execution sequences
  - Actual commands to run (pytest commands, etc.)
  - Intermediate verification gates
  - Common pitfalls for that task type
- This would be guidance for agents on HOW to execute work
- But orchestration skill is guidance for orchestrators on HOW to delegate work

**Clarification Provided**:

- User: "Sorry i want to clarify. Its not a how to I execute this task. This is the orchestrator skill not an agent skill."
- Templates should answer: "How do I, as orchestrator, craft an effective Task prompt for this type of work?"
- Templates would specify:
  - What context to provide (WHAT/WHY)
  - What constraints to set (WHERE/WHEN)
  - What success criteria to define
  - What NOT to include (preserve agency)
  - How to structure verification checkpoints

**Resolution/Consensus**:

- Delegation templates guide orchestrators in crafting Task prompts
- Execution protocols already exist in slash commands (am-i-complete.md, is-it-done.md) for agents
- Orchestrator references slash commands rather than duplicating their content
- Templates preserve agent autonomy by specifying success criteria (WHAT "done" means) not methodology (HOW to get there)

**Key Insight**: Delegation templates are orchestrator-facing (how to delegate effectively); execution protocols are agent-facing (how to verify work). Orchestration skill contains delegation guidance, not execution guidance.

### Topic 5: Success Criteria vs Micromanagement

**Initial Question/Problem**: Orchestrator's examples of verification requirements included prescriptive text like "Before claiming completion: Provide test that failed before fix, Provide same test passing after fix, Provide full test suite results"

**Points Raised**:

- This text is prescriptive micromanagement of agent's verification process
- Sub-agents already have verification protocols (am-i-complete.md, is-it-done.md)
- The text is "dilute guidance that doesn't apply to all situations, but is asked for on all tasks"

**Misunderstanding Identified**:

- Orchestrator conflated:
  - Micromanagement: telling agents HOW to implement solution and WHAT evidence format to provide
  - Success criteria: defining WHAT constitutes completion
- Orchestrator's example criteria were:
  - Too narrow and limiting ("only for scenario when task is addressing a known bug")
  - Not universal but presented as applying to all fix tasks
  - Prescriptive about verification methodology rather than outcome-focused

**Clarification Provided**:

- User: "Micromanagement is telling them how to implement their solution. Providing a (definition of done|definition of success|validation protocol for that task) is project management best practice, and provides more autonomy regarding how to reach that point of success."
- Micromanagement (BAD): "Use pytest to create a test", "First write failing test, then implement fix"
- Clear success criteria (GOOD): "Bug reproduces in test before fix", "Same test passes after fix", "Full test suite passes"
- Providing clear success criteria gives MORE autonomy because:
  - Agent knows exactly what "done" means
  - Agent chooses their own approach
  - Agent can self-validate throughout work
  - No guessing or back-and-forth about expectations

**Resolution/Consensus**:

- Success criteria should be:
  - Task-specific (not universal checklists)
  - Outcome-focused (what success looks like)
  - Testable/observable (can be verified)
  - NOT prescriptive about methodology
- Even within "fix:" commit type, different scenarios require different success criteria:
  - Reproducible bug fix: test that reproduces → test that passes
  - Performance fix: baseline → improvement → threshold met
  - Documentation fix: examples execute → links work → tested instructions
  - Configuration fix: loads without errors → system operates → backward compatible
- Orchestrator must understand specific scenario and craft success criteria accordingly, not copy-paste generic criteria

**Key Insight**: Clear success criteria enable autonomy by defining the destination without prescribing the route. This is project management best practice that gives agents more agency, not less.

### Topic 6: Role of Slash Commands in Verification

**Initial Question/Problem**: Orchestrator's delegation examples duplicated content from slash commands (exit code definitions, core principles, verification checklists) in Task prompts.

**Points Raised**:

- Slash commands (/am-i-complete, /is-it-done) already contain universal verification guidance
- Duplicating this content bloats Task prompts
- Violates DRY principle and creates maintenance burden

**Misunderstanding Identified**:

- Orchestrator was copying core definitions and verification principles into every Task prompt:
  - Exit code 0 definitions
  - "Works" and "fixed" definitions
  - Common gotchas
  - Universal verification checklists
- This duplicates content that already exists in canonical slash command files

**Clarification Provided**:

- User: "Why would you need to put that in every prompt when you have claude code commands?"
- User: "All universal boilerplate agent guidance, such as definitions of 'works' and 'fixed', and common gotchas. Would go into slash commands for task state self assessment."
- Correct approach: reference the slash commands, don't duplicate their content
- Same pattern as "follow guidelines from @~/.claude/CLAUDE.md" - point to authoritative source

**Resolution/Consensus**: Clean separation of concerns:

**Slash Commands contain universal guidance**:

- Core definitions: "works", "fixed", "done"
- Exit code 0 ≠ success
- Common gotchas: "passes linters" ≠ works
- Task-type verification checklists (fix, feature, refactor, etc.)
- Evidence requirements
- Quality gates
- Red flags

**Orchestrator Task Prompts contain task-specific context**:

- Success criteria for THIS specific task
- THIS bug/feature/scenario details
- Reference to appropriate slash command: "Use /is-it-done to validate your work"
- No duplication of universal definitions

**Agent workflow**:

1. Receives task with specific success criteria
2. Works autonomously toward those criteria
3. Before reporting "done", runs /is-it-done
4. Slash command loads universal verification protocol
5. Agent self-validates against task-specific criteria AND universal standards
6. Reports completion with evidence

**Key Insight**: Universal truth lives in one canonical place (slash commands); task prompts stay focused on what's unique to THIS task. This prevents bloat and ensures consistency.

## Decisions Made

### Documentation Changes

1. **Story-based-framing removal**: Eliminated all unvalidated methodology references (63 lines) from 7 files in agent-orchestration directory
   - Rationale: n=1 sample size, no comparative baseline, definitive claims without verification
   - Files affected: synthesis-improvements-from-research.md, analysis-\*.md files
   - Verification: Grep confirms zero remaining references

2. **Timeline language removal**: Replaced "Week 1/2/3", "Next Sprint" with dependency-based priority ordering
   - Rationale: Timelines meaningless for AI agent work; execution rate depends on parallelization strategy
   - File affected: comparative-analysis-synthesis.md
   - Replacement structure: Priority levels with explicit dependencies and parallelization markers

3. **MCP tool guidance clarification**: Reformatted SKILL.md lines 336-343 as verbatim template text
   - Rationale: Prevent orchestrators from prescribing specific MCP functions agents should use
   - Change: "Proactively identify and leverage available MCP tools from your `<functions>` list"
   - Committed: `docs(agent-orchestration): clarify MCP tool guidance as verbatim template`

### File Creations

1. **post-completion-validation-protocol.md**: Comprehensive verification protocol covering all 11 conventional commit types (fix, feat, refactor, docs, test, chore, perf, ci, build, style, revert)
   - Purpose: Reference for orchestrators to understand what verification evidence to expect by task type
   - Structure: IF-THEN format with 2-4 specific verification bullets per type
   - Supporting sections: Red flags, verification workflow, quality gates, evidence collection, orchestrator response templates

### Patterns Identified

1. **Hallucination triggers documented**:
   - **Story-based anti-pattern framing**: Unvalidated claims propagate through agent analysis chains
   - **Timeline language**: "Week 1/2/3", "Sprint" references in AI agent work plans
   - **Incomplete verification**: Agent claims "all files searched" but actual verification reveals gaps
   - **Authority mimicry**: Surface features of professional analysis without underlying verification

2. **Delegation anti-patterns**:
   - Prescribing specific MCP functions instead of pointing to discovery
   - Duplicating slash command content in Task prompts
   - Providing universal checklists instead of task-specific success criteria
   - Conflating verification methodology (HOW) with success criteria (WHAT)

## Unresolved Questions

### Multi-Step Workflows with Verification Gates

User raised research task example requiring progressive verification:

- Phase 1: Exploration (discover sources) → Checkpoint 1
- Phase 2: Collection (gather information) → Checkpoint 2
- Phase 3: Synthesis (analyze findings) → Checkpoint 3
- Phase 4: Documentation (create citable report) → Final verification

Question: How should orchestrators structure Task prompts for multi-phase work requiring intermediate checkpoints?

Partial resolution discussed:

- Include checkpoint requirements in Task prompt upfront
- Agent self-validates at each checkpoint before proceeding
- Orchestrator can verify sub-progress before allowing continuation
- Prevents collecting from bad sources, proceeding with incomplete data, creating uncitable reports

Action item: Expand research task example into full delegation template

### Task-Type-Specific Delegation Templates

Question: Should agent-orchestration skill include delegation templates for each conventional commit type showing "How do I craft an effective Task prompt for this type of work?"

Structure discussed:

- `/agent-orchestration/delegation-templates/`
  - `research-task-delegation.md`
  - `fix-task-delegation.md`
  - `feat-task-delegation.md`
  - `perf-task-delegation.md`

Each would include:

- INCLUDE in Task Prompt: Context (WHAT/WHY), Constraints (WHERE/WHEN), Success Criteria, Verification Checkpoints
- DO NOT INCLUDE: Specific search queries, prescribed order, internal organization methods, analysis frameworks, step-by-step implementation
- Verification Gates: What checkpoints to build into delegation

Action item: Determine if these templates provide value or create maintenance burden

### Post-Completion-Validation-Protocol Usage

Question: How should orchestrators use post-completion-validation-protocol.md?

Two potential uses:

1. **Post-completion**: What to check AFTER agent reports "done"
2. **Pre-delegation**: Source material for crafting task-specific success criteria to include in Task prompts upfront

Resolution discussed:

- Protocol should be source material for defining success criteria
- Success criteria go into Task prompts upfront (not sprung on agent after claiming completion)
- Agent works toward clear criteria, self-validates throughout
- Agent reports completion with evidence against stated criteria
- Orchestrator validates evidence matches upfront criteria

Action item: Clarify protocol's role and ensure documentation reflects pre-delegation usage pattern

## Key Insights

### Hallucination Prevention Patterns

1. **Timeline language is red flag**: Any reference to "Week N", "Sprint N", "X minutes/hours/days" in AI agent work plans indicates pattern-matching from human project management conventions without reasoning about actual work
   - Detection question: "Does this serve semantic function (describing task properties) or aesthetic function (looking professional)?"

2. **Unvalidated claims in AI-facing docs compound**: When AI models consume false information from skills/documentation, they treat it as fact, propagate it through reasoning chains, and create false feedback loops

3. **Exit code 0 ≠ success**: Core principle to prevent pattern-matching failures where agents treat "didn't crash" as "works correctly"
   - Must test actual functional behavior against specific success criteria

### Delegation Patterns

1. **Success criteria enable autonomy**: Providing clear, testable success criteria gives agents MORE autonomy by defining destination without prescribing route
   - Micromanagement: prescribing HOW/tools/steps
   - Empowerment: defining WHAT constitutes completion

2. **Reference vs duplicate**: Orchestrator should point to authoritative sources (slash commands, skills, docs) rather than duplicating their content in Task prompts
   - Same pattern as `@~/.claude/CLAUDE.md` references
   - Prevents bloat and ensures consistency

3. **Discovery vs prescription for tools**: Orchestrator can't know what MCP functions agent has, so must point agent to discover rather than prescribe specific tools
   - Correct: "Proactively identify and leverage available MCP tools"
   - Incorrect: "Use WebFetch for gathering sources"

4. **Task-specific vs universal criteria**: Success criteria must be crafted for specific scenario, not copy-pasted generic checklists
   - Even within same commit type (fix), different scenarios require different criteria
   - Orchestrator must understand scenario and craft accordingly

### Verification Protocols

1. **Slash commands contain universal truth**: Core definitions, common gotchas, task-type verification checklists live in canonical slash command files
   - `/am-i-complete` provides step-by-step verification workflows with actual commands
   - `/is-it-done` provides task-type-specific verification questions and quality gates
   - Agents reference these for self-validation

2. **Pre-delegation vs post-completion**: Success criteria should be provided upfront in Task prompt, not sprung on agent after claiming completion
   - Agent uses criteria to self-validate throughout work
   - Agent knows when actually done
   - Reports completion with evidence against stated criteria
   - Orchestrator validates evidence matches upfront criteria

3. **Evidence-based completion**: "Done" means evidence demonstrates success criteria met, not "should work", "passes linters", "exit code 0"

## Cross-References

### Files Referenced

- `./agent-orchestration/SKILL.md` (lines 336-343, 338)
- `./agent-orchestration/hallucination-triggers.md` (Category 2: Timeline Language, Category 4: Incomplete Verification)
- `./agent-orchestration/post-completion-validation-protocol.md`
- `./agent-orchestration/comparative-analysis-synthesis.md`
- `~/.claude/commands/am-i-complete.md`
- `~/.claude/commands/is-it-done.md`
- `~/.claude/CLAUDE.md` (rule: "The model must never state timelines or estimates for task completion")

### Commits

- `docs(agent-orchestration): clarify MCP tool guidance as verbatim template` (commit 81f79ac)
  - Changed SKILL.md lines 336-343
  - Added "Proactively identify" phrasing
  - Formatted as code fence to indicate verbatim template text

### Agents Used

- `claude-context-optimizer` (7 parallel instances for story-based-framing removal, 1 for timeline removal, 1 for validation protocol creation)
- `technical-researcher` (created comparative-analysis-synthesis.md)

## Patterns for Future Application

### Orchestrator Self-Check Questions

Before delegating to sub-agent, orchestrator should verify:

1. **Success criteria defined?** Can agent self-validate when done?
2. **Task-specific or generic?** Are criteria crafted for THIS scenario or copy-pasted universal checklist?
3. **Outcome or methodology?** Am I defining WHAT "done" means or HOW to get there?
4. **Duplicating slash commands?** Am I copying content that already exists in canonical source?
5. **Prescribing tools?** Am I telling agent WHICH functions to use instead of pointing to discovery?
6. **Timeline language?** Do I reference "Week N", "Sprint N", time estimates?

### Verification Protocol Pattern

For any task delegation:

**In Task Prompt**:

- Success Criteria: [task-specific, testable outcomes]
- Verification: Use /is-it-done to validate your work

**NOT in Task Prompt**:

- Universal definitions (already in slash commands)
- Specific tools to use (agent discovers)
- Step-by-step methodology (agent decides)
- Generic checklists (craft task-specific criteria)

**Agent Workflow**:

1. Receive task with specific success criteria
2. Work autonomously toward criteria
3. Self-validate using /is-it-done before claiming done
4. Report completion with evidence against stated criteria

**Orchestrator Response**:

- Validate evidence matches upfront criteria
- If insufficient: specify what additional evidence needed (based on criteria already stated)
- If sufficient: accept completion

## Conclusion

This discussion established critical distinctions in AI agent orchestration:

1. **Autonomy enablement**: Clear success criteria provide MORE autonomy by defining destination without prescribing route - this is project management best practice, not micromanagement

2. **Verification timing**: Success criteria belong in Task prompts upfront (enabling agent self-validation throughout) rather than post-completion checklists sprung on agents

3. **Discovery vs prescription**: Orchestrators point agents to discover available resources rather than prescribing specific tools they can't know about

4. **Reference vs duplication**: Universal truth lives in canonical sources (slash commands); task prompts stay focused on task-specific context

5. **Hallucination prevention**: Timeline language and unvalidated claims in AI-facing documentation are red flags requiring removal

The session resulted in concrete improvements to agent-orchestration skill (SKILL.md verbatim template formatting, story-based-framing removal, timeline language elimination) and established patterns for future orchestration work.
