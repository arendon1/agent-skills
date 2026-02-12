# Google Scholar Search Guide

## Overview

Google Scholar provides the most comprehensive coverage across disciplines. This guide details search strategies and best practices.

## Basic Search

```bash
# Search for papers on a topic
python scripts/search_google_scholar.py "CRISPR gene editing" \
  --limit 50 \
  --output results.json

# Search with year filter
python scripts/search_google_scholar.py "machine learning protein folding" \
  --year-start 2020 \
  --year-end 2024 \
  --limit 100 \
  --output ml_proteins.json
```

## Advanced Search Strategies

* **Exact phrases**: Use quotation marks for exact phrases: `"deep learning"`
* **Author search**: Use `author:LeCun`
* **Title search**: Use `intitle:"neural networks"`
* **Exclusions**: Use `-` to exclude terms: `machine learning -survey`
* **Site search**: Use `site:arXiv.org`, `source:Nature`
* **Date ranges**: Use `2020..2024` in query or flags.

### Advanced Operators

```
"exact phrase"           # Exact phrase matching
author:lastname          # Search by author
intitle:keyword          # Search in title only
source:journal           # Search specific journal
-exclude                 # Exclude terms
OR                       # Alternative terms
2020..2024              # Year range
```

## Best Practices

1. **Find Seminal Papers**:
    * Sort by citation count (most cited first).
    * Check "Cited by" for impact assessment.
2. **Use specific terms**: Include key technical terms and acronyms.
3. **Recent work**: Filter by recent years for fast-moving fields.
4. **Reviews**: Search for `intitle:review` to get overviews.

## Example Searches

```bash
# Find recent reviews on a topic
"CRISPR" intitle:review 2023..2024

# Find papers by specific author on topic
author:Church "synthetic biology"

# Find highly cited foundational work
"deep learning" 2012..2015 sort:citations

# Exclude surveys and focus on methods
"protein folding" -survey -review intitle:method
```
