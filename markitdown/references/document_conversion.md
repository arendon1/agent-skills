# Document Conversion

Convert Office documents and PDFs to Markdown while preserving structure.

**Supported formats:**
- PDF files (with optional Azure Document Intelligence integration)
- Word documents (DOCX)
- PowerPoint presentations (PPTX)
- Excel spreadsheets (XLSX, XLS)

**Basic usage:**
```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("document.pdf")
print(result.text_content)
```

**Command-line:**
```bash
markitdown document.pdf -o output.md
```
