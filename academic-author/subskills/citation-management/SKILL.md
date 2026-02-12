---
name: citation-management
description: Comprehensive citation management for academic research. Search Google Scholar, PubMed, extract metadata, form BibTeX, and validate citations.
allowed-tools: [Read, Write, Edit, Bash]
---

# Citation Management

## Overview

Manage citations systematically throughout the research and writing process. This skill provides tools for searching academic databases (Google Scholar, PubMed), extracting accurate metadata, validating citation information, and generating properly formatted BibTeX entries.

**Core Capabilities:**

1. **Search**: Find papers on Google Scholar and PubMed.
2. **Extract**: Convert DOIs/PMIDs/URLs to complete BibTeX.
3. **Format**: Clean and standardize BibTeX files.
4. **Validate**: Check for errors, broken DOIs, and duplicates.

## Core Workflow

### Phase 1: Search

Detailed Guides:

* [Google Scholar Search](references/google_scholar_search.md): `scripts/search_google_scholar.py`
* [PubMed Search](references/pubmed_search.md): `scripts/search_pubmed.py`

```bash
# Google Scholar
python scripts/search_google_scholar.py "topic" --limit 50 --output results.json

# PubMed with MeSH
python scripts/search_pubmed.py --query '"Topic"[MeSH]' --output results.json
```

### Phase 2: Metadata Extraction

Detailed Guide: [Metadata Extraction](references/metadata_extraction.md)

```bash
# From DOI/PMID/ArXiv/URL
python scripts/extract_metadata.py --doi 10.1038/nature12345
python scripts/extract_metadata.py --pmid 12345678
python scripts/extract_metadata.py --arxiv 2301.00000

# Batch from file
python scripts/extract_metadata.py --input ids.txt --output refs.bib
```

### Phase 3: BibTeX Formatting

Detailed Guide: [BibTeX Formatting](references/bibtex_formatting.md)

```bash
# Clean, Sort, Deduplicate
python scripts/format_bibtex.py raw.bib \
  --deduplicate \
  --sort year \
  --output clean.bib
```

### Phase 4: Validation

Detailed Guide: [Citation Validation](references/citation_validation.md)

```bash
# Check accuracy and fix common errors
python scripts/validate_citations.py clean.bib \
  --auto-fix \
  --report report.json \
  --output final.bib
```

## Quick Reference: Scripts and Tools

| Script | Purpose |
| :--- | :--- |
| `search_google_scholar.py` | Search Google Scholar for papers. |
| `search_pubmed.py` | Search PubMed using E-utilities. |
| `extract_metadata.py` | Get metadata from identifiers (DOI, PMID, etc.). |
| `doi_to_bibtex.py` | Fast DOI-to-BibTeX conversion. |
| `format_bibtex.py` | Clean, sort, and deduplicate BibTeX files. |
| `validate_citations.py` | Verify accuracy and find errors. |

## Integration

This skill is designed to be orchestrated by the **Academic Author** skill.

* **Academic Author**: Writing and structure.
* **Citation Management**: Reference accuracy and formatting.
* **Scientific Schematics**: Diagram generation.

See `../academic-author/SKILL.md` for the overarching workflow.
