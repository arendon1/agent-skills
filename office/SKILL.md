---
name: office
description: >-
  Generates Office documents (DOCX, XLSX, PDF, PPTX) using pure TypeScript libraries.
  Use when creating reports, spreadsheets, presentations, or PDFs from data.
license: Apache-2.0
metadata:
  version: "1.0.0"
  trit: 1
  author: agent-builder
allowed-tools: [Read, Write, Edit, Bash]
---

# Office Document Generation

## Overview

Generate Microsoft Office documents and PDFs programmatically with TypeScript. All libraries are pure JavaScript with zero native dependencies, enabling universal runtime support.

**Supported Formats:**

* **DOCX**: `docx` (Word)
* **XLSX**: `xlsx` (Excel/SheetJS)
* **PDF**: `pdf-lib` (PDF)
* **PPTX**: `pptxgenjs` (PowerPoint)

## Core Capabilities

### 1. Word Documents (DOCX)

Generate reports, invoices, and letters with formatting, tables, and images.

* **Guide**: [references/docx.md](references/docx.md)

### 2. Spreadsheets (XLSX)

Create data-heavy spreadsheets with formulas and multiple sheets.

* **Guide**: [references/xlsx.md](references/xlsx.md)

### 3. PDF Documents

Create PDFs from scratch, fill forms, or merge existing PDFs.

* **Guide**: [references/pdf.md](references/pdf.md)

### 4. Presentations (PPTX)

Build slide decks with charts, tables, and shapes.

* **Guide**: [references/pptx.md](references/pptx.md)

## Integration Guides

### Cloudflare Workers

Deploy document generation to the edge.

* **Guide**: [references/cloudflare_workers.md](references/cloudflare_workers.md)

## Quick Start

```bash
# Install all libraries
npm install docx xlsx pdf-lib pptxgenjs
```

## Critical Rules

### Always Do

* ✅ Use `await Packer.toBuffer(doc)` for DOCX.
* ✅ Remember PDF coordinates start at **BOTTOM-LEFT**.
* ✅ Use `type: 'buffer'` for XLSX in Workers/Browser.
* ✅ Embed fonts in PDF before using them.
* ✅ Set proper `Content-Type` headers for downloads.

### Never Do

* ❌ Use `Packer.toBuffer()` without `await`.
* ❌ Assume PDF y=0 is at the top.
* ❌ Use `writeFile` (Node.js only) in Workers/Browser.
* ❌ Use remote image URLs in PPTX on Workers (use base64).

## Package Versions

Verified 2026-01-12:

* `docx`: ^9.5.0
* `xlsx`: ^0.18.5
* `pdf-lib`: ^1.17.1
* `pptxgenjs`: ^4.0.1
