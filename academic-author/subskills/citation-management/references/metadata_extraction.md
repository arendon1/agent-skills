# Metadata Extraction Guide

## Overview

Convert paper identifiers (DOI, PMID, arXiv ID) to complete, accurate metadata.

## Supported Identifiers

* **DOI**: Primary source (via CrossRef).
* **PMID**: Biomedical papers (via PubMed).
* **arXiv ID**: Preprints (via arXiv API).
* **URL**: Web pages (basic metadata).

## Usage Commands

```bash
# Extract from DOI
python scripts/extract_metadata.py --doi 10.1038/s41586-021-03819-2

# Extract from PMID
python scripts/extract_metadata.py --pmid 34265844

# Extract from arXiv ID
python scripts/extract_metadata.py --arxiv 2103.14030

# Batch extraction from file
python scripts/extract_metadata.py --input identifiers.txt --output citations.bib
```

## Metadata Sources

1. **CrossRef API**: Best for DOIs. Publisher-provided data (authors, title, journal, volume, pages, dates).
2. **PubMed E-utilities**: Best for biomedical IDs. Includes MeSH terms, abstracts.
3. **arXiv API**: Complete metadata for preprints, version tracking.
4. **DataCite API**: For datasets and software DOIs.

## Best Practices

1. **Always use DOIs when available**: They are permanent and have the best metadata.
2. **Verify extracted data**: Check author accents, journal abbreviations, and page numbers.
3. **Handle Preprints**: If a preprint is later published, update the metadata to the published version.
4. **Consistency**: Maintain consistent author name formats (Last, First) and journal abbreviations.
