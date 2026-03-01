---
name: document-manager
description: >-
  The ultimate toolset for managing, converting, and manipulating multi-format documents (PDF, DOCX, PPTX, XLSX, Markdown).
  Use when reading, extracting text/tables, creating, editing, or performing advanced operations (OCR, merge, split, recalc, slide generation) on office and PDF files.
  Triggers include: Word docs, Excel spreadsheets, PowerPoint decks, PDF manipulation, and MarkItDown conversion requests.
metadata:
  version: "1.0.0"
  language: en
  trit: 0
  risk_tier: CAUTION
---

# Document Manager

A unified skill for comprehensive document processing. This skill consolidates capabilities for Word, Excel, PowerPoint, PDF, and general Markdown conversion.

## 🚀 Self-Deployment & Bootstrapping

If this skill's document workflows are not appearing in your agent's slash-commands, run the following command from the skill's root directory:
`python scripts/bootstrap.py --workspace .`

This will automatically detect your agent's configuration directory (e.g., `.agents`, `.cursor`, `.gemini`, or `.agent`) and deploy the necessary `.md` or `.mdc` files.

## 📚 Specialized Guides (References)

For deep-dives into specific formats, refer to these internal guides:

| Format | Reference Guide | Key Capabilities |
| :--- | :--- | :--- |
| **PDF** | [pdf.md](references/pdf.md) | OCR, form filling, merging, splitting, extraction |
| **Word** | [docx.md](references/docx.md) | Templates, comments, tracked changes, formatting |
| **Excel** | [xlsx.md](references/xlsx.md) | Formula handling, financial modeling, recalculation |
| **Slides** | [pptx.md](references/pptx.md) | Deck creation, master layouts, visual QA, thumbnails |
| **Markdown** | [markitdown.md](references/markitdown.md) | Universal conversion to LLM-friendly formats |

## ⚙️ Core Utilities

### MarkItDown (Universal Reader)

Use for quick text extraction from any supported format.

```bash
uv run markitdown document.pdf -o document.md
```

### Office Manipulators (Scripts)

Specialized tools for direct file manipulation are located in `scripts/`:

- `scripts/office/`: Shared low-level XML processing tools.
- `scripts/pdf/`: PDF specific helpers.
- `scripts/pptx/`: Slide generation and cleanup.
- `scripts/xlsx/`: Excel formula recalculation.
- `scripts/docx/`: Word template management.

## 🚀 Quick Reference

| Action | Target Format | Tool/Script |
| :--- | :--- | :--- |
| Extract All Text | Any | `markitdown` |
| Recalc Formulas | XLSX | `scripts/xlsx/recalc.py` |
| Visual Slide QA | PPTX | `scripts/pptx/thumbnail.py` |
| Merge/Split | PDF | `pypdf` (via reference guide) |
| Accept Changes | DOCX | `scripts/docx/accept_changes.py` |

## QA & Validation

Always verify output integrity. For PPTX and XLSX, use the specialized QA scripts mentioned in their respective guides to ensure visual and calculation accuracy.
