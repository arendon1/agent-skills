# Citation Validation Guide

## Overview

Verify that all citations are accurate, complete, and resolve to actual publications.

## Validation Commands

```bash
# Basic validation
python scripts/validate_citations.py references.bib

# Auto-fix common issues
python scripts/validate_citations.py references.bib --auto-fix --output fixed.bib

# Detailed report
python scripts/validate_citations.py references.bib --report report.json --verbose
```

## Validation Checks

1. **DOI Verification**: Checks if DOI resolves via `doi.org` and metadata matches CrossRef.
2. **Required Fields**: Ensures all mandatory fields for the entry type are present.
3. **Data Consistency**: Checks years, page formats, and author names.
4. **Duplicate Detection**: Finds same papers cited with different keys.
5. **Format Compliance**: Valid BibTeX syntax check.

## Common Validation Errors

* **Invalid DOI**: The DOI does not exist. (Action: FIND correct DOI).
* **Missing Field**: E.g., missing `journal` or `year`. (Action: Add missing info).
* **Duplicate**: Two entries for the same paper. (Action: Merge references).
* **Formatting**: Syntax errors often break LaTeX compilation. (Action: Fix braces/commas).

## Best Practices

* Validate early and often.
* Use `--auto-fix` carefully; check the output.
* Resolve all "high severity" errors before submission.
