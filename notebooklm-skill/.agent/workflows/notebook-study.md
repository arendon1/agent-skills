---
description: Active learning session with quizes, flashcards, and audio for a specific notebook
---
# Notebook Study Workflow

## Study Session

1. **Invoke Bridge**:
   - Audio Brief: `python C:/Users/andres.rendon/Documents/Prompts/skills/notebooklm-skill/scripts/unified_bridge.py artifact --notebook-id <ID> --type audio`
   - Quizes: `python C:/Users/andres.rendon/Documents/Prompts/skills/notebooklm-skill/scripts/unified_bridge.py artifact --notebook-id <ID> --type quiz`
   - Flashcards: `python C:/Users/andres.rendon/Documents/Prompts/skills/notebooklm-skill/scripts/unified_bridge.py artifact --notebook-id <ID> --type flashcards`
2. **Active Learning**: Review the generated content and iterate on weak points.
