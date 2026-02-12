# Platform Guide

## Platform-Specific Workflows

### GitHub

**Pull Requests:**
```bash
# Install GitHub CLI
# https://cli.github.com/

# Create PR
gh pr create
gh pr create --title "Title" --body "Description"
gh pr create --base main --head feature-branch

# List PRs
gh pr list

# View PR
gh pr view
gh pr view <number>

# Check out PR locally
gh pr checkout <number>

# Review PR
gh pr review
gh pr review --approve
gh pr review --request-changes
gh pr review --comment

# Merge PR
gh pr merge
gh pr merge --squash
gh pr merge --rebase
gh pr merge --merge

# Close PR
gh pr close <number>
```

**GitHub Actions:**
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: npm test
```

### Azure DevOps

**Pull Requests:**
```bash
# Install Azure DevOps CLI
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Create PR
az repos pr create --title "Title" --description "Description"
az repos pr create --source-branch feature --target-branch main

# List PRs
az repos pr list

# View PR
az repos pr show --id <id>

# Complete PR
az repos pr update --id <id> --status completed

# Branch policies
az repos policy list
az repos policy create --config policy.json
```

**Azure Pipelines:**
```yaml
# azure-pipelines.yml
trigger:
  - main
pool:
  vmImage: 'ubuntu-latest'
steps:
  - script: npm test
    displayName: 'Run tests'
```

### Bitbucket

**Pull Requests:**
```bash
# Create PR (via web or Bitbucket CLI)
bb pr create

# Review PR
bb pr list
bb pr view <id>

# Merge PR
bb pr merge <id>
```

**Bitbucket Pipelines:**
```yaml
# bitbucket-pipelines.yml
pipelines:
  default:
    - step:
        script:
          - npm test
```

### GitLab

**Merge Requests:**
```bash
# Install GitLab CLI (glab)
# https://gitlab.com/gitlab-org/cli

# Create MR
glab mr create
glab mr create --title "Title" --description "Description"

# List MRs
glab mr list

# View MR
glab mr view <id>

# Merge MR
glab mr merge <id>

# Close MR
glab mr close <id>
```

**GitLab CI:**
```yaml
# .gitlab-ci.yml
stages:
  - test
test:
  stage: test
  script:
    - npm test
```

## Cross-Platform Considerations

### Line Endings

```bash
# Windows (CRLF in working directory, LF in repository)
git config --global core.autocrlf true

# macOS/Linux (LF everywhere)
git config --global core.autocrlf input

# No conversion (not recommended)
git config --global core.autocrlf false

# Use .gitattributes for consistency
# .gitattributes:
* text=auto
*.sh text eol=lf
*.bat text eol=crlf
```

### Case Sensitivity

```bash
# macOS/Windows: Case-insensitive filesystems
# Linux: Case-sensitive filesystem

# Enable case sensitivity in Git
git config --global core.ignorecase false

# Rename file (case-only change)
git mv --force myfile.txt MyFile.txt
```

### Path Handling

```bash
# Git always uses forward slashes internally
# Works on all platforms:
git add src/components/Header.jsx

# Windows-specific tools may need backslashes in some contexts
```

### Git Bash / MINGW Path Conversion (Windows)

**CRITICAL: Git Bash is the primary Git environment on Windows!**

Git Bash (MINGW/MSYS2) automatically converts Unix-style paths to Windows paths for native executables.

**Controlling Path Conversion:**

```bash
# Method 1: MSYS_NO_PATHCONV (Git for Windows only)
# Disable ALL path conversion for a command
MSYS_NO_PATHCONV=1 git command --option=/path

# Method 2: MSYS2_ARG_CONV_EXCL (MSYS2)
# Exclude specific argument patterns
export MSYS2_ARG_CONV_EXCL="*"              # Exclude everything

# Method 3: Manual conversion with cygpath
cygpath -u "C:\path"     # → Unix format: /c/path
cygpath -w "/c/path"     # → Windows format: C:\path

# Method 4: Workarounds
# Use double slashes: //e //s instead of /e /s
# Use dash notation: -e -s instead of /e /s
# Quote paths with spaces: "/c/Program Files/file.txt"
```
