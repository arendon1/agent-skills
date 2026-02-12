name: academic-author
description: >-
  Orchestrates specialized sub-agents to research, write, and refine high-quality academic publications.
  Use when user wants to write a paper, needs IMRaD structure, or requests "write a research document".
license: Apache-2.0
metadata:
  version: "1.0.0"
  trit: 0
  author: agent-builder
allowed-tools: [Read, Write, Edit, Bash]
compatibility: Requires agent-orchestration skill
---

# Academic Author

## Overview

The **Academic Author** is a high-level orchestrator designed to produce publication-quality scientific documents. It coordinates specialized sub-skills to handle every aspect of the academic workflow.

**Primary Responsibilities:**

1. **Orchestration**: Directs specialized agents (`citation-management`, `typst-writer`, `scientific-schematics`).
2. **Research Design**: Helps formulate questions and methodology ([Guide](references/research-design.md)).
3. **Writing & Structure**: Enforces IMRaD structure and academic style ([Guide](references/writing-guide.md)).
4. **Publishing**: Strategizes journal selection and peer review responses ([Guide](references/publishing.md)).

## The "Author" Suite

This skill doesn't work alone. It acts as the lead author, delegating tasks to:

| Role | Skill | Responsibility |
| :--- | :--- | :--- |
| **The Librarian** | `citation-management` | Finding papers, extracting metadata, validating citations. |
| **The Editor** | `typst-writer` | Typesetting, formatting, PDF generation. |
| **The Illustrator** | `scientific-schematics` | Generating scientific diagrams and flowcharts. |
| **The Analyst** | `office` | Creating data tables (XLSX) or supplementals. |

## Delegation Protocol

When orchestrating these sub-skills, **ALWAYS** follow the `agent-orchestration` principles:

1. **Define Success**: Be clear about output format (e.g., "Valid BibTeX file", "Compiled PDF").
2. **Provide Context**: Explain *why* the task is needed (e.g., "for the Methodology section").
3. **Trust Expertise**: Don't micromanage the *how*. Let the specialized skill handle the execution.

**Example Delegation Prompt:**
> "Role: `citation-management` (The Librarian).
> Context: We are writing the Literature Review for a paper on Agentic AI.
> Task: Find 5 seminal papers from 2024-2025 regarding 'Multi-Agent Orchestration'.
> Success: Return a validated list with abstracts and a BibTeX file."

## Core Workflows

### 1. Writing a Paper (Start to Finish)

1. **Plan**: Use [references/research-design.md](references/research-design.md) to define scope.
2. **Draft**: Write content following [references/writing-guide.md](references/writing-guide.md).
3. **Cite**: Call `citation-management` to find and validate references.
4. **Visualize**: Call `scientific-schematics` to generate needed figures.
5. **Publish**: Call `typst-writer` to compile the final PDF.

### 2. Literature Review

1. **Search**: `citation-management` -> `search_google_scholar.py`.
2. **Synthesize**: Group findings thematically (not chronologically).
3. **Write**: Draft the review section.

### 3. Submission

1. **Check**: Validate citations with `citation-management`.
2. **Format**: Ensure `typst-writer` template matches journal requirements.
3. **Cover Letter**: Draft using [references/publishing.md](references/publishing.md).

## Usage Examples

**Scenario: "Write a paper on AI Agents."**
> "I will act as the **Academic Author**. First, I'll structure the paper. Then, I'll ask **Citation Management** to find key papers from 2024. I'll have **Scientific Schematics** draw the architecture diagram, and finally use **Typst Writer** to compile the PDF."

## Reference Guides

* [Writing Guide](references/writing-guide.md): IMRaD, Style, Pitfalls.
* [Research Design](references/research-design.md): Questions, Ethics, Methodology.
* [Publishing Strategy](references/publishing.md): Journals, Peer Review, Cover Letters.
