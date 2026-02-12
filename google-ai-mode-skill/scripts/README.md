# Google AI Mode Scripts

Python utilities for querying Google AI Search.

## Scripts

- **run.py**: Wrapper for all scripts (handles venv activation)
- **search.py**: Main search interface

## Usage

Always use via wrapper:

```bash
python scripts/run.py search.py --query "..." [flags]
```

## Available Flags

- `--save`: Auto-save to results/TIMESTAMP_Query.md
- `--debug`: Save verbose logs to logs/
- `--show-browser`: Open visible window to solve CAPTCHAs
- `--json`: Include JSON metadata in output

See parent SKILL.md for flag documentation and query strategies.

## Development

Virtual environment is managed automatically by run.py.
See requirements.txt for dependencies.
