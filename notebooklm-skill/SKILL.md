---
name: notebooklm-skill
description: >-
  Orchestrates deep research and synthesis across complex document libraries (PDFs, docs, web).
  Use for multi-source analysis, grounded report generation, cross-referencing archives, or creating study aids from large document sets.
  Handles project discovery, source ingestion, and grounded reasoning for comprehensive research tasks.
license: Apache-2.0
metadata:
  version: "1.0.0"
  language: en
  trit: 0
  author: agent-builder
---

# NotebookLM Research Assistant

Interact with Google NotebookLM to query your documentation library.

## 🚀 Self-Deployment & Bootstrapping

If this skill's research workflows (like `/notebook-research`, `/notebook-study`) are not appearing in your agent's slash-commands, run the following command from the skill's root directory:
`python scripts/run.py bootstrap.py --workspace .`

This will automatically detect your agent's configuration directory (e.g., `.agents`, `.cursor`, `.gemini`, or `.agent`) and deploy the necessary `.md` or `.mdc` files.

## Essential Commands

**ALWAYS use `scripts/run.py` wrapper.**

### 1. Unified Interface (Recommendation)

Use the new bridge for all operations. It handles authentication automatically from storage.

```bash
python scripts/run.py unified_bridge.py list
python scripts/run.py unified_bridge.py create --title "Project Beta"
python scripts/run.py unified_bridge.py ask --notebook-id [ID] --question "..."
```

### 2. Research & Learning Workflows

Invoke these from the workspace root for high-level orchestration:

- `/notebook-research [TOPIC]`: Deep dive research and source aggregation.
- `/notebook-study [ID]`: Active learning with quizes/flashcards.
- `/notebook-visualize [ID]`: Generate Mind-Maps.

### 3. Artifact Generation

```bash
python scripts/run.py unified_bridge.py artifact --notebook-id [ID] --type audio
python scripts/run.py unified_bridge.py artifact --notebook-id [ID] --type quiz
python scripts/run.py unified_bridge.py artifact --notebook-id [ID] --type mind-map
```

## Workflow

1. **Discover / Sync**: **ALWAYS** run `python scripts/run.py unified_bridge.py list` first to see existing NotebookLM projects. Do not create new ones blindly; be aware of what is already present!
2. **Research**: Call `/notebook-research` to initialize.
3. **Optimize**: Use `/gh-learn` to find secondary sources and add them.
4. **Study**: Run `/notebook-study` to verify comprehension.
5. **Visualize**: Use `/notebook-visualize` for architectural insight.

## References

- [references/troubleshooting.md](references/troubleshooting.md): Common errors & fixes
- [references/usage_patterns.md](references/usage_patterns.md): Advanced workflows
