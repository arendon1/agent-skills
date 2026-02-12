# Advanced Integrations

Enhance conversion quality with AI-powered features.

**Azure Document Intelligence:**
For enhanced PDF processing with better table extraction and layout analysis:
```python
from markitdown import MarkItDown

md = MarkItDown(docintel_endpoint="<endpoint>", docintel_key="<key>")
result = md.convert("complex.pdf")
```

**LLM-Powered Image Descriptions:**
Generate detailed image descriptions using GPT-4o:
```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")
result = md.convert("presentation.pptx")  # Images described with LLM
```
