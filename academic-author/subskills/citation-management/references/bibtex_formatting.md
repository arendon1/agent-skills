# BibTeX Formatting Guide

## Overview

Generate clean, preferably formatted BibTeX entries (`.bib`).

## Common Entry Types

* **@article**: Journal articles. Required: author, title, journal, year.
* **@book**: Books. Required: author/editor, title, publisher, year.
* **@inproceedings**: Conference papers. Required: author, title, booktitle, year.
* **@misc**: Preprints, software, datasets, websites.

## Example Entries

```bibtex
@article{Smith2024,
  author  = {Smith, John and Doe, Jane},
  title   = {{The Title with Capitalization Preserved}},
  journal = {Journal of Examples},
  year    = {2024},
  volume  = {10},
  number  = {3},
  pages   = {123--145},
  doi     = {10.1234/example}
}

@inproceedings{Jones2023,
  author    = {Jones, Alice},
  title     = {Conference Paper Title},
  booktitle = {Proceedings of the Conference},
  year      = {2023},
  pages     = {1--10}
}
```

## Formatting & Cleaning Commands

```bash
# Format and clean
python scripts/format_bibtex.py references.bib --output formatted.bib

# Sort entries
python scripts/format_bibtex.py references.bib --sort key --output sorted.bib

# Remove duplicates
python scripts/format_bibtex.py references.bib --deduplicate --output clean.bib
```

## Formatting Rules

1. **Citation Keys**: Use meaningful keys like `FirstAuthorYearKeyword` (e.g., `Vaswani2017Attention`).
2. **Capitalization**: Protect acronyms and proper nouns in titles with braces: `{CRISPR}` or `{{Whole Title}}`.
3. **Page Ranges**: Use double dashes: `123--145`.
4. **Authors**: Use `and` to separate authors: `Author One and Author Two`.
5. **Deduplication**: Remove duplicate entries based on DOI or Title/Year.
