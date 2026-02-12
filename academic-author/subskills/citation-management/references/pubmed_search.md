# PubMed Search Guide

## Overview

PubMed specializes in biomedical and life sciences literature (35+ million citations). It supports precise searching using MeSH terms and field tags.

## Basic Search

```bash
# Search PubMed
python scripts/search_pubmed.py "Alzheimer's disease treatment" \
  --limit 100 \
  --output alzheimers.json

# Search with MeSH terms and filters
python scripts/search_pubmed.py \
  --query '"Alzheimer Disease"[MeSH] AND "Drug Therapy"[MeSH]' \
  --date-start 2020 \
  --date-end 2024 \
  --publication-types "Clinical Trial,Review" \
  --output alzheimers_trials.json
```

## Advanced Querying

### MeSH Terms

MeSH (Medical Subject Headings) provides controlled vocabulary.

* Find terms at [MeSH Browser](https://meshb.nlm.nih.gov/search).
* Use in queries: `"Diabetes Mellitus, Type 2"[MeSH]`.

### Field Tags

* `[Title]`: Search in title only.
* `[Title/Abstract]`: Search in title or abstract.
* `[Author]`: Search by author name (`"Smith J"[Author]`).
* `[Journal]`: Search specific journal.
* `[Publication Date]`: Date range (`2020:2024[Publication Date]`).
* `[Publication Type]`: Article type (`"Review"[Publication Type]`, `"Clinical Trial"[Publication Type]`).

### Complex Query Examples

```bash
# Clinical trials on diabetes treatment published recently
"Diabetes Mellitus, Type 2"[MeSH] AND "Drug Therapy"[MeSH] 
AND "Clinical Trial"[Publication Type] AND 2020:2024[Publication Date]

# Reviews on CRISPR in specific journal
"CRISPR-Cas Systems"[MeSH] AND "Nature"[Journal] AND "Review"[Publication Type]

# Specific author's recent work
"Smith AB"[Author] AND cancer[Title/Abstract] AND 2022:2024[Publication Date]
```

## Automation with E-utilities

The scripts use NCBI E-utilities API:

* **ESearch**: Find PMIDs.
* **EFetch**: Get full metadata.
* **ELink**: Find related articles.
