# ADR 0002: HTML to Markdown Conversion — markdownify as Internal Dependency

## Status

Accepted

## Context

Moodle `page` modules contain rich HTML content (headings, paragraphs, images, tables, embedded videos). The extracted content must be stored as markdown files for human readability and agent consumption.

Options considered:
- `markdownify` (Python library)
- `html2text`
- Custom BeautifulSoup walker
- Raw HTML storage

## Decision

Use `markdownify` as a declared dependency of the skill. Added to `requirements.txt` / `pyproject.toml` of the skill, not as a global project dependency.

## Rationale

- Handles tables, links, images, lists correctly
- Lightweight (~1 dependency)
- Active maintenance
- Better table output than `html2text`

## Consequences

- Skill carries its own dependency list. User installs via `pip install -r gestionar-cursos/requirements.txt`.
- If `markdownify` becomes unmaintained, we can swap to `html2text` or custom walker with minimal code changes (wrapper function).

## Notes

Dependency declared in `gestionar-cursos/requirements.txt`:
```
markdownify>=0.13
```
