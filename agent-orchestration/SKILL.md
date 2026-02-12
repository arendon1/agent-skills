---
name: agent-orchestration
description: This skill should be used when the model's ROLE_TYPE is orchestrator and needs to delegate tasks to specialist sub-agents. Provides scientific delegation framework ensuring world-building context (WHERE, WHAT, WHY) while preserving agent autonomy in implementation decisions (HOW). Use when planning task delegation, structuring sub-agent prompts, or coordinating multi-agent workflows.
---

# Agent Orchestration

**Provide world-building context (WHERE, WHAT, WHY). Define success criteria. Trust agent expertise for implementation (HOW).**

## 📚 References

| Reference | Purpose |
| :--- | :--- |
| `references/principles.md` | Core scientific method & delegation principles |
| `references/is-it-done-checklist.md` | Completion criteria checklist |
| `references/validation-protocol.md` | Post-completion validation |
| `references/clear-framework.md` | CLEAR delegation framework |
| `references/hallucination-triggers.md` | Avoiding common triggers |

## 🛠️ Delegation Template

Start every Task prompt with:

`Your ROLE_TYPE is sub-agent.`

**Full template structure:**

```text
Your ROLE_TYPE is sub-agent.

[Task identification]

OBSERVATIONS:
- [Factual observations from your work or other agents]
- [Verbatim error messages if applicable]
- [Observed locations: file:line references if already known]
- [Environment or system state if relevant]

DEFINITION OF SUCCESS:
- [Specific measurable outcome]
- [Acceptance criteria]
- [Verification method]
- Solution follows existing patterns found in [reference locations]
- Solution maintains or reduces complexity

CONTEXT:
- Location: [Where to look]
- Scope: [Boundaries of the task]
- Constraints: [User requirements only]

YOUR TASK:
1. Run SlashCommand /is-it-done to understand completion criteria for this task type
2. Use the /is-it-done checklists as your working guide throughout this task
3. Perform comprehensive context gathering using:
   - Available functions and MCP tools from the <functions> list
   - Relevant skills from the <available_skills> list
   - Project file exploration and structure analysis
   - External resources (CI/CD logs, API responses, configurations)
4. Form hypothesis based on gathered evidence
5. Design and execute experiments to test hypothesis
6. Verify findings against authoritative sources
7. Implement solution following discovered best practices
8. Verify each /is-it-done checklist item as you complete it
9. Only report completion after all /is-it-done criteria satisfied with evidence

INVESTIGATION REQUIREMENTS:
- Trace the issue through the complete stack before proposing fixes
- Document discoveries at each layer (e.g., UI → Logic → System → Hardware)
- Identify both symptom AND root cause
- Explain why addressing [root] instead of patching [symptom]
- If proposing workaround, document why root cause cannot be fixed

VERIFICATION REQUIREMENTS:
- /is-it-done is step 1 of YOUR TASK - run it before starting work
- Use /is-it-done checklists as working guide, not post-mortem report
- Provide evidence for each checklist item as you complete it
- If checklist reveals missing work, complete that work before proceeding
- Your work will be reviewed by a rigorous engineer who expects verified functionality

AVAILABLE RESOURCES:
[See below for examples]
```

## Writing Effective AVAILABLE RESOURCES

The AVAILABLE RESOURCES section provides world-building context about the environment, not a restrictive tool list.

**Correct pattern (world-building, empowering):**

```text
AVAILABLE RESOURCES:
- The `gh` CLI is pre-authenticated for GitHub operations (issues, PRs, API queries)
- Excellent MCP servers are installed for specialized tasks - check your <functions> list and prefer MCP tools (like `Ref`, `context7`, `exa`) over built-in alternatives since they're specialists at their domain
- This Python project uses `uv` for all operations - activate the `uv` skill and use `uv run python` instead of `python3`, `uv pip` instead of `pip`
- Project uses `hatchling` as build backend - activate the `hatchling` skill for build/publish guidance
- This repository uses GitLab CI - use `gitlab-ci-local` to validate pipeline changes locally before pushing
- Recent linting fixes are documented in `.claude/reports/` showing common issues and resolutions
- Package validation scripts live in `./scripts/` - check its README.md for available validators to run after changes
- Full project context available including tests, configs, and documentation
```

## Specialized Agent Assignments

**For Context Gathering:**
- Use `context-gathering` sub-agent to gather context without polluting orchestrator's context window

**For Python Development:**
- Use `python-cli-architect` sub-agent to write Python code
- Use `python-pytest-architect` sub-agent to plan and write Python tests
- Use `python-code-reviewer` sub-agent for post-write code review

**For Bash Development:**
- Use `bash-script-developer` sub-agent to write bash scripts
- Use `bash-script-auditor` sub-agent for post-write script review

**For Documentation:**
- Use `documentation-expert` sub-agent to write user-facing documentation

**For Architecture:**
- Use `system-architect` sub-agent for system architecture documentation
- For Python architecture, use `python-cli-architect` instead

**For Linting Issues:**
- Use `linting-root-cause-resolver` sub-agent for pre-commit, ruff, mypy, pytest issues

**Critical Rule:**
The orchestrator must task sub-agents with ALL code changes, including the smallest edits, and any context gathering or research.
