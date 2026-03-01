---
name: github-cli
description: >-
  The definitive skill for interacting with GitHub via the `gh` CLI.
  Extends agent capabilities to explore repositories, manage issues/PRs, search code,
  and extract deep knowledge without visual navigation or cloning.
  Use when exploring a new repository, checking project status, reviewing PRs,
  or searching for specific logic across GitHub.
metadata:
  version: "1.0.0"
  language: en
  trit: 0
  risk_tier: CAUTION
---

# github-cli: Efficient GitHub Mastery

**`github-cli`** leverages the official GitHub CLI (`gh`) to provide high-bandwidth, low-latency interaction with GitHub repositories. It enforces a "CLI-First" approach to save tokens and avoid the inaccuracies of visual navigation.

## When to Use

- **Learning from Code**: Use `/gh-learn <URL>` to extract a structured knowledge artifact from any repo.
- **Repository Exploration**: Probing structure, dependencies, and entry points.
- **Project Management**: Listing issues, PRs, and search code snippets.
- **CLI Setup**: When `gh` is missing, use the internal setup logic to install it.

## Core Patterns

### 1. Repository Learning (The `/gh-learn` Workflow)

```bash
python scripts/gh_explorer.py https://github.com/owner/repo
```

### 2. General GitHub Management

```bash
# Search code
python scripts/gh_manager.py search "keyword" owner/repo

# List open Issues
python scripts/gh_manager.py issues owner/repo

# Review PR Diff
python scripts/gh_manager.py pr-diff owner/repo 123
```

### 3. Environment Setup

```bash
python scripts/setup_gh.py --install
```

## Quick Reference

| Action | CLI Command / Script |
| ------ | ------------------- |
| Learn Repo | `/gh-learn <URL>` |
| Setup GH | `python scripts/setup_gh.py --install` |
| View Repo | `gh repo view <repo>` |
| Search Code | `gh search code <query>` |
| List PRs | `gh pr list` |
| API Call | `gh api <endpoint>` |

## Rules & Constraints

1. **Strictly Prohibited**: Never try to navigate GitHub visually if `gh` is available.
2. **Setup First**: Always check `gh --version` before attempting operations. If missing, offer `setup_gh.py`.
3. **Recursive API**: Use `gh api` with `recursive=1` for tree exploration to minimize round-trips.
4. **Knowledge Artifacts**: When learning a repo, always produce a `knowledge_<repo>.md` file in the current workspace.
