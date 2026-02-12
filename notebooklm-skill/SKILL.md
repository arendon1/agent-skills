---
name: notebooklm-skill
description: >-
  Queries Google NotebookLM for source-grounded answers from uploaded PDFs, docs, and web content.
  Use when analyzing large documents, synthesizing reports from multiple sources, or querying knowledge bases.
license: Apache-2.0
metadata:
  version: "1.0.0"
  trit: 0
  author: agent-builder
compatibility: Requires browser for authentication
---

# NotebookLM Research Assistant

Interact with Google NotebookLM to query your documentation library.

## Essential Commands

**ALWAYS use `scripts/run.py` wrapper.**

### 1. Authentication

Check status first. If failed, run setup (browser will open).

```bash
python scripts/run.py auth_manager.py status
python scripts/run.py auth_manager.py setup   # Opens browser for login
```

### 2. Library Management

```bash
# List all notebooks
python scripts/run.py notebook_manager.py list

# Search library
python scripts/run.py notebook_manager.py search --query "project specs"
```

### 3. Adding Notebooks

**Smart Add** (Recommended if details unknown):

1. Query URL first: `python scripts/run.py ask_question.py --question "Describe content" --notebook-url URL`
2. Add with details: `python scripts/run.py notebook_manager.py add --url URL ...`

**Manual Add** (All fields required):

```bash
python scripts/run.py notebook_manager.py add \
  --url "https://notebooklm..." \
  --name "Project Alpha" \
  --description "Technical specs and architecture" \
  --topics "specs,architecture,2026"
```

### 4. Asking Questions

```bash
# Query specific notebook
python scripts/run.py ask_question.py --question "What are the API limits?" --notebook-id [ID]

# Query by URL (Temporary session)
python scripts/run.py ask_question.py --question "Summary of findings" --notebook-url "https://..."
```

## Workflow

1. **Check Auth**: `auth_manager.py status`
2. **Locate/Add Notebook**: `notebook_manager.py`
3. **Query**: `ask_question.py`
4. **Follow-up**: If answer ends with "Is that ALL?", analyze gaps and ask follow-ups.

## References

- [references/troubleshooting.md](references/troubleshooting.md): Common errors & fixes
- [references/usage_patterns.md](references/usage_patterns.md): Advanced workflows
