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

## 🚀 Quick Start

**Basic Conversion:**

```python
from markitdown import MarkItDown
md = MarkItDown()
result = md.convert("document.pdf")
print(result.text_content)
```

**Command Line:**

```bash
markitdown document.pdf -o output.md
```

**YouTube Transcript:**

```python
result = md.convert("https://youtube.com/watch?v=VIDEO_ID")
```

## 📦 Installation

**Full installation:**

```bash
uv pip install 'markitdown[all]'
```

**Modular installation:**

```bash
uv pip install 'markitdown[pdf]'    # PDF
uv pip install 'markitdown[docx]'   # Word
uv pip install 'markitdown[audio]'  # Audio
```
