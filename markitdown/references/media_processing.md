# Media Processing

Extract text from images using OCR and transcribe audio files to text.

**Supported formats:**
- Images (JPEG, PNG, GIF, etc.) with EXIF metadata extraction
- Audio files with speech transcription (requires speech_recognition)

**Image with OCR:**
```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("image.jpg")
print(result.text_content)  # Includes EXIF metadata and OCR text
```

**Audio transcription:**
```python
result = md.convert("audio.wav")
print(result.text_content)  # Transcribed speech
```
