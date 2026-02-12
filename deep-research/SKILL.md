---
name: deep-research
description: >-
  Orchestrates multi-step deeply recursive research using browser agents, Google AI, and Perplexity.
  Use when simple search is insufficient and verified citations, market intelligence, or academic papers are required.
license: Apache-2.0
metadata:
  version: "1.0.0"
  trit: 1
  author: agent-builder
allowed-tools: [Read, Write, Edit, Bash]
compatibility: Requires Python 3.10+ and Bun for scripts
---

# Deep Research Professional

## Overview

High-capability research agent for market intelligence, company analysis, and competitive research. Automates data collection, verification, and report generation using a suite of advanced tools.

## Integrated Capabilities

This skill works best when combined with specialized tools:

1. **Google AI Mode**: Use for *initial* broad discovery, library documentation, and finding recent 2026 data.
2. **Perplexity (Sonar)**: Use for *intelligent* answers, deep reasoning, and comparative analysis.
3. **NotebookLM**: Use for *deep* semantic analysis of uploaded PDF/Doc reports or synthesizing large documentation sets.
4. **Deep Research Scripts**: Use for *structured* data extraction and formal report generation.

## Capabilities & Commands

### 1. Academic Research (NEW)

Find peer-reviewed papers, methodologies, and datasets.

```bash
# Find papers on a topic
bun scripts/academic-researcher.ts --topic "AI Agents" --focus "methodology"

# Solve CAPTCHA if needed (opens browser)
bun scripts/academic-researcher.ts --topic "AI Agents" --show-browser
```

### 2. Intelligent Lookups (Perplexity)

Use Perplexity's Sonar models for reasoning and fact-checking.

```bash
# General lookup (Auto-selects Pro/Reasoning model)
python scripts/research_lookup.py "Explain the mechanism of CRISPR off-target effects"

# Force Deep Reasoning
python scripts/research_lookup.py "Compare mRNA vs Traditional Vaccines" --force-model reasoning
```

### 3. Company Analysis

Deep dive into specific companies for job prep, investment, or partnership.

```bash
# Analyze financial health
bun scripts/company-analyzer.ts --company "Marriott" --focus "financial"
```

### 4. Market & Web Research

Broad research on markets, trends, or tools.

```bash
# General multi-source search
bun scripts/web-researcher.ts --query "hotel market trends 2024" --depth comprehensive
```

## Advanced Gathering Workflow

For complex topics, use this "Triangulation" pattern:

1. **Scout (Google/Perplexity)**:
    * Use `google-ai-mode-skill` or `research_lookup.py` to get high-level trends.
    * `python scripts/research_lookup.py "[Topic] key trends 2026"`

2. **Deep Dive (Deep Research)**:
    * Use `web-researcher.ts` to crawl specific high-value domains.
    * `bun scripts/web-researcher.ts --query "[Specific Aspect]" --depth comprehensive`

3. **Synthesize (NotebookLM)**:
    * Upload large PDF reports to NotebookLM.
    * `python ../notebooklm-skill/scripts/run.py ask_question.py --question "Extract financial KPIs" --notebook-url "[URL]"`

## Methodology & Standards

See [references/methodology.md](references/methodology.md) for full details on:

* Source Quality Criteria (Authority, Timeliness, Objectivity)
* Citation Formats & Link Tracking
* Ethical Research Guidelines

## Available Tools

* `scripts/research_lookup.py`: **NEW** Perplexity Sonar integration.
* `scripts/academic-researcher.ts`: Academic paper discovery & PDF extraction.
* `scripts/company-analyzer.ts`: Targeted entity analysis.
* `scripts/web-researcher.ts`: General broad crawler/summarizer.
* `scripts/report-generator.ts`: Formatter for gathered data.
