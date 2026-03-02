# Web Content Extraction

Convert web-based content and e-books to Markdown.

**Supported formats:**
- HTML files and web pages
- YouTube video transcripts (via URL)
- EPUB books
- RSS feeds

**YouTube transcript:**
```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("https://youtube.com/watch?v=VIDEO_ID")
print(result.text_content)
```
