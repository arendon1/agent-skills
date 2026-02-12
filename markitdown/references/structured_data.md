# Structured Data Handling

Convert structured data formats to readable Markdown tables.

**Supported formats:**
- CSV files
- JSON files
- XML files

**CSV to Markdown table:**
```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("data.csv")
print(result.text_content)  # Formatted as Markdown table
```
