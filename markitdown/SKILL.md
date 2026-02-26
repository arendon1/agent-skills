---
name: markitdown
description: >-
  Converts PDF, Office, Images, Audio, and Web content to clean Markdown for LLM processing.
  Use when needing to read, extract text, transcribe, or process files into context-friendly format.
license: Apache-2.0
metadata:
  version: "1.0.0"
  trit: 0
  author: agent-builder
---

# MarkItDown

**Convert various file formats into Markdown optimized for LLM processing.**

## 📚 References

| Reference | Purpose |
| :--- | :--- |
| `references/document_conversion.md` | PDF, DOCX, PPTX, XLSX conversion |
| `references/media_processing.md` | Image OCR and Audio transcription |
| `references/web_content.md` | HTML, YouTube, EPUB extraction |
| `references/structured_data.md` | CSV, JSON, XML to Markdown tables |
| `references/advanced_integrations.md` | Azure Doc Intelligence & LLM Image descriptions |

## ⚙️ Setup & Validation

Before using MarkItDown, you MUST ensure the environment is correctly configured. This repository uses **Deterministic Tooling** to manage dependencies.

**Run the validation script:**

```bash
python scripts/ensure_markitdown.py
```

This script will:

1. Check for an existing global installation.
2. Check for the package in your current Python environment.
3. If missing, automatically create a `.venv` and install `markitdown[all]` using `uv`.

## 🚀 Quick Start

**Using the CLI (Preferred):**

```bash
# If using a local venv created by the setup script
uv run markitdown document.pdf -o output.md

# Or directly if in PATH
markitdown document.pdf -o output.md
```

**Python Usage:**

```python
from markitdown import MarkItDown
md = MarkItDown()
result = md.convert("document.pdf")
print(result.text_content)
```

## 📦 Manual Installation

While the `ensure_markitdown.py` script is preferred, you can install manually using `uv`:

```bash
uv pip install 'markitdown[all]'
```

*Note: For Windows users, 'uv' is the recommended package manager for speed and reliability.*
