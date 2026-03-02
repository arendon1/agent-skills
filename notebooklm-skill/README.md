<div align="center">

# NotebookLM Agentic AI Skill

**Enable your AI agent (Antigravity, Kilo, Copilot) to chat directly with NotebookLM for source-grounded answers based exclusively on your uploaded documents**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Agentic Skill](https://img.shields.io/badge/Agentic-Skill-purple.svg)](https://github.com/PleasePrompto/notebooklm-skill)
[![Based on](https://img.shields.io/badge/Based%20on-NotebookLM%20MCP-green.svg)](https://github.com/PleasePrompto/notebooklm-mcp)

> Use this skill to query your Google NotebookLM notebooks directly from your AI agent for source-grounded, citation-backed answers. Includes browser automation, library management, and persistent authentication. Drastically reduces hallucinations by answering only from your uploaded documents.

[Installation](#installation) • [Quick Start](#quick-start) • [Why NotebookLM](#why-notebooklm-not-local-rag) • [How It Works](#how-it-works) • [MCP Alternative](https://github.com/PleasePrompto/notebooklm-mcp)

</div>

---

## ⚠️ Important: Local Execution Only

**This skill works ONLY with local agent installations that have direct script execution capabilities.**

The skill requires network access for browser automation. You must run this skill locally on your machine to allow the agent to interact with the Python environment.

---

## The Problem

When you tell an AI agent to "search through my local documentation", here's what happens:

- **Massive token consumption**: Searching means reading multiple files repeatedly.
- **Inaccurate retrieval**: Matches keywords but misses context and cross-document connections.
- **Hallucinations**: Without strict grounding, models invent plausible-sounding details.
- **Manual copy-paste**: Constant switching between the browser and your terminal.

## The Solution

This Agentic AI Skill lets your tools chat directly with [**NotebookLM**](https://notebooklm.google/) — Google's knowledge base powered by Gemini that provides intelligent, synthesized answers exclusively from your uploaded documents.

```
Your Task → Agent asks NotebookLM → Gemini synthesizes answer → Agent performs task with grounded data
```

**No more copy-paste dance**: Your agent asks questions directly and gets answers back in the CLI/Chat. It builds deep understanding through automatic follow-ups, getting specific implementation details, edge cases, and best practices.

---

## Why NotebookLM, Not Local RAG?

| Approach | Token Cost | Setup Time | Hallucinations | Answer Quality |
|----------|------------|------------|----------------|----------------|
| **Feed docs to LLM** | 🔴 Very high (multiple file reads) | Instant | Yes - fills gaps | Variable retrieval |
| **Web search** | 🟡 Medium | Instant | High - unreliable sources | Hit or miss |
| **Local RAG** | 🟡 Medium-High | Hours (embeddings, chunking) | Medium - retrieval gaps | Depends on setup |
| **NotebookLM Skill** | 🟢 Minimal | 5 minutes | **Minimal** - source-grounded | Expert synthesis |

### What Makes NotebookLM Superior?

1. **Pre-processed by Gemini**: Upload docs once, get instant expert knowledge.
2. **Natural language Q&A**: Not just retrieval — actual understanding and synthesis.
3. **Multi-source correlation**: Connects information across 50+ documents.
4. **Citation-backed**: Every answer includes source references.
5. **No infrastructure**: No vector DBs, embeddings, or complex chunking strategies needed.

---

## Installation

### Simple Installation

```bash
# 1. Clone this repository into your agent's skills directory
git clone https://github.com/PleasePrompto/notebooklm-skill.git

# 2. Navigate to the directory
cd notebooklm-skill

# 3. Use the unified runner
python scripts/run.py unified_bridge.py list
```

When you first use the skill, it automatically:

- Creates an isolated Python environment (`.venv`)
- Installs all dependencies including **Google Chrome**
- Sets up browser automation for maximum reliability
- Everything stays contained in the skill folder

---

## Quick Start

### 1. Check your library

Ask your agent:
*"Show my available NotebookLM notebooks"*

### 2. Authenticate (one-time)

Run:
*"Set up NotebookLM authentication"* or `python scripts/run.py auth_manager.py login`
*A Chrome window opens → log in with your Google account*

### 3. Create your knowledge base

Go to [notebooklm.google.com](https://notebooklm.google.com) → Create notebook → Upload your docs:

- 📄 PDFs, Google Docs, markdown files
- 🔗 Websites, YouTube videos, GitHub repos
- 📚 Multiple sources per notebook

### 4. Direct Research

```bash
python scripts/run.py unified_bridge.py ask --notebook-id [ID] --question "What are the core findings?"
```

---

## How It Works

This is an **Agentic AI Skill** - a local directory containing instructions (`SKILL.md`) and scripts that an agent can invoke.

### Architecture

```
notebooklm-skill/
├── SKILL.md              # Instructions for the agent
├── scripts/              # Python automation scripts
│   ├── ask_question.py   # Query NotebookLM
│   ├── notebook_manager.py # Library management
│   └── bridge.py         # Unified interface
├── .venv/                # Isolated Python environment (auto-created)
└── data/                 # Local notebook library and browser state
```

### Core Technology

- **Patchright**: Professional browser automation (Playwright-based)
- **Python**: Implementation language for maximum flexibility
- **Human-Like Automation**: Realistic interaction patterns to ensure reliability

---

## Common Intents

| Prompt Intent | Underlying Action |
|--------------|--------------|
| *"Summarize my research papers"* | Queries the relevant notebook |
| *"Sync my NotebookLM notebooks"* | Discovery through `unified_bridge list` |
| *"Create a mind-map from these docs"* | Artifact generation |
| *"Add this URL to NotebookLM"* | Source ingestion |

---

## Troubleshooting

If you encounter issues, run:
`python scripts/run.py cleanup_manager.py all`
to reset the session and browser state.

---

## Disclaimer

This tool automates browser interactions with NotebookLM. It behaves naturally with human-like delays and mouse movements. I recommend using a dedicated Google account for automated research tasks.

AI agents are powerful assistants, not infallible oracles. Always review critical data synthesized from your sources.

---

<div align="center">

Built for **Antigravity**, **Kilo**, and other next-generation AI agents.

Stop the copy-paste dance. Start getting accurate, grounded answers.

</div>
