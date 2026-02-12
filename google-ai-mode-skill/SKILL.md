---
name: google-ai-mode-skill
description: >-
  Retrieves comprehensive, source-grounded answers from Google's AI Search with inline citations.
  Use when needing post-cutoff knowledge, API documentation, or real-time implementation patterns.
license: Apache-2.0
metadata:
  version: "1.0.0"
  trit: 1
  author: agent-builder
compatibility: Requires python scripts/run.py wrapper
---

# Google AI Mode Skill

Retrieves AI-generated overviews from Google Search with citations.

## Usage

**ALWAYS use `scripts/run.py` wrapper.**

```bash
# Standard Search (Recommended)
python scripts/run.py search.py --query "React 19 features 2026 (actions, useFormStatus)" --save --debug

# Custom Output Path
python scripts/run.py search.py --query "..." --output result.md

# Show Browser (Run this if you get CAPTCHA errors)
python scripts/run.py search.py --query "test" --show-browser
```

## Flags

- `--save`: Auto-save to `results/TIMESTAMP_Query.md`
- `--debug`: Save verbose logs to `logs/` (Essential for troubleshooting)
- `--show-browser`: Open visible window to solve CAPTCHAs manually
- `--json`: Include JSON metadata in output

## Query Strategy

Google AI Mode requires specific, detailed queries for best results.
**Template**: `[Topic] [Year] ([Aspect 1], [Aspect 2]). [Format].`

*Example*: "Next.js 15 routing 2026 (parallel routes, intercepting routes). Provide code examples."

See [references/usage-guide.md](references/usage-guide.md) for full optimization strategies.
