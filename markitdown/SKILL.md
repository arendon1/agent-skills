---
name: markitdown
description: Convert various file formats (PDF, Office documents, images, audio, web content, structured data) to Markdown optimized for LLM processing. Use when converting documents to markdown, extracting text from PDFs/Office files, transcribing audio, performing OCR on images, extracting YouTube transcripts, or processing batches of files. Supports 20+ formats including DOCX, XLSX, PPTX, PDF, HTML, EPUB, CSV, JSON, images with OCR, and audio with transcription.
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
