# NotebookLM Skill Usage Patterns

Advanced patterns for using the NotebookLM skill effectively within any agentic framework.

## Critical: Always Use run.py

**Every command must use the run.py wrapper to ensure the virtual environment and dependencies are correctly loaded:**

```bash
# ✅ CORRECT:
python scripts/run.py auth_manager.py status
python scripts/run.py ask_question.py --question "..."

# ❌ WRONG:
python scripts/auth_manager.py status  # Will fail due to missing dependencies!
```

## Pattern 1: Initial Setup

```bash
# 1. Check authentication
python scripts/run.py auth_manager.py status

# 2. If not authenticated, setup (Browser window will open)
python scripts/run.py auth_manager.py setup
# Note: Manually log in to Google in the appearing Chrome window.

# 3. Add first notebook
python scripts/run.py notebook_manager.py add \
  --url "https://notebooklm.google.com/notebook/..." \
  --name "Project Documentation" \
  --description "Core technical docs for the current project" \
  --topics "architecture,api,setup"
```

## Pattern 2: Smart Discovery

When an agent receives a NotebookLM URL, it should perform discovery before adding it to the library:

```bash
# 1. Query the notebook to discover its purpose
python scripts/run.py ask_question.py \
  --question "Identify the core themes, covered topics, and target audience of this notebook." \
  --notebook-url "[URL]"

# 2. Use discovered info to add it with rich metadata
python scripts/run.py notebook_manager.py add \
  --url "[URL]" \
  --name "[Discovered Name]" \
  --description "[Discovered Purpose]" \
  --topics "[Extracted Keywords]"
```

## Pattern 3: Deep Research Loop (Recursive Follow-up)

NotebookLM often prompts with "Is that ALL you need to know?" if there is more hidden context. The agent should handle this recursively:

```python
# 1. Ask initial comprehensive question
# 2. Analyze response for the "Is that ALL you need to know?" prompt
# 3. If present, ask for more specific details or edge cases
python scripts/run.py ask_question.py \
  --question "Tell me more about the implementation details of X based on the previous context."
```

## Pattern 4: Comparison Research

```bash
# Compare facts across two different knowledge bases
python scripts/run.py ask_question.py --question "What is the policy for X?" --notebook-id notebook-a
python scripts/run.py ask_question.py --question "What is the policy for X?" --notebook-id notebook-b

# Synthesize the delta between the two sources.
```

## Best Practices

### 1. Question Formulation

- Be specific and request structured (JSON/Markdown) responses.
- Include the desired output format in the `--question` string.

### 2. Notebook Management

- Use descriptive names and tag notebooks with clear topics for searchability.
- Keep URLs current and ensure they are shared with at least "Viewer" permissions.

### 3. Performance & Limits

- Standard accounts are limited to ~50 queries per day.
- Use `python scripts/run.py cleanup_manager.py` if the browser session becomes unstable.

### 4. Security

- Use a dedicated Google account for automated research.
- Never commit the `data/` directory to version control.
