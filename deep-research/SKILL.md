---
name: deep-research
description: >-
  Executes deep market, company, and ACADEMIC research using automated browser agents and Google AI Mode.
  Use when researching companies, analyzing competitors, finding academic papers,
  evaluating software tools, or gathering comprehensive market intelligence.
---

# Deep Research Professional

## Overview

High-capability research agent for market intelligence, company analysis, and competitive research. Automates data collection, verification, and report generation.

## Integrated Capabilities

This skill works best when combined with specialized tools:

1. **Google AI Mode**: Use for *initial* broad discovery, library documentation, and finding recent 2026 data.
2. **NotebookLM**: Use for *deep* semantic analysis of uploaded PDF/Doc reports or synthesizing large documentation sets.
3. **Deep Research Scripts**: Use for *structured* data extraction and formal report generation.

## Capabilities & Commands

### 1. Academic Research (NEW)

Find peer-reviewed papers, methodologies, and datasets.

```bash
# Find papers on a topic
bun scripts/academic-researcher.ts --topic "AI Agents" --focus "methodology"

# Solve CAPTCHA if needed (opens browser)
bun scripts/academic-researcher.ts --topic "AI Agents" --show-browser

# Find literature reviews
bun scripts/academic-researcher.ts --topic "Climate Change" --focus "literature-review"
```

### 2. Company Analysis

Deep dive into specific companies for job prep, investment, or partnership.

```bash
# Analyze financial health
bun scripts/company-analyzer.ts --company "Marriott" --focus "financial"

# Analyze market position
bun scripts/company-analyzer.ts --company "Marriott" --focus "market-position"
```

### 3. Market & Web Research

Broad research on markets, trends, or tools.

```bash
# General multi-source search
bun scripts/web-researcher.ts --query "hotel market trends 2024" --depth comprehensive

# Find specific developments
bun scripts/web-researcher.ts --query "Marriott recent acquisitions" --depth recent
```

### 4. Report Generation

Compile findings into structured markdowns.

```bash
bun scripts/report-generator.ts --template market-analysis --input research-data.json
```

## Advanced Gathering Workflow

For complex topics, use this "Triangulation" pattern:

1. **Scout (Google AI Mode)**:
    * Use `google-ai-mode-skill` to get a high-level overview and list of key sources.
    * `python ../google-ai-mode-skill/scripts/run.py search.py --query "[Topic] key trends 2026" --save`

2. **Deep Dive (Deep Research)**:
    * Use `web-researcher.ts` to crawl the specific high-value domains identified in Step 1.
    * `bun scripts/web-researcher.ts --query "[Specific Aspect]" --depth comprehensive`

3. **Synthesize (NotebookLM)**:
    * If you find large PDF reports, upload them to NotebookLM.
    * Use `notebooklm-skill` to query them for precise answers.
    * `python ../notebooklm-skill/scripts/run.py ask_question.py --question "Extract financial KPIs" --notebook-url "[URL]"`

## Methodology & Standards

See [references/research-methodology.md](references/research-methodology.md) for full details on:

* Source Quality Criteria (Authority, Timeliness, Objectivity)
* Citation Formats & Link Tracking
* Ethical Research Guidelines

## Available Tools

* `scripts/academic-researcher.ts`: Academic paper discovery & PDF extraction
* `scripts/company-analyzer.ts`: Targeted entity analysis
* `scripts/web-researcher.ts`: General broad crawler/summarizer
* `scripts/report-generator.ts`: Formatter for gathered data
