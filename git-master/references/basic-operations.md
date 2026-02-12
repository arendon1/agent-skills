# Basic Git Operations

## Repository Initialization and Cloning

```bash
# Initialize new repository
git init
git init --initial-branch=main  # Specify default branch name

# Clone repository
git clone <url>
git clone <url> <directory>
git clone --depth 1 <url>  # Shallow clone (faster, less history)
git clone --branch <branch> <url>  # Clone specific branch
git clone --recurse-submodules <url>  # Include submodules
```

## Configuration

```bash
# User identity (required for commits)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Default branch name
git config --global init.defaultBranch main

# Line ending handling (Windows)
git config --global core.autocrlf true  # Windows
git config --global core.autocrlf input  # macOS/Linux

# Editor
git config --global core.editor "code --wait"  # VS Code
git config --global core.editor "vim"

# Diff tool
git config --global diff.tool vscode
git config --global difftool.vscode.cmd 'code --wait --diff $LOCAL $REMOTE'

# Merge tool
git config --global merge.tool vscode
git config --global mergetool.vscode.cmd 'code --wait $MERGED'

# Aliases
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual '!gitk'

# View configuration
git config --list
git config --global --list
git config --local --list
git config user.name  # Get specific value
```

## Basic Workflow

```bash
# Check status
git status
git status -s  # Short format
git status -sb  # Short with branch info

# Add files
git add <file>
git add .  # Add all changes in current directory
git add -A  # Add all changes in repository
git add -p  # Interactive staging (patch mode)

# Remove files
git rm <file>
git rm --cached <file>  # Remove from index, keep in working directory
git rm -r <directory>

# Move/rename files
git mv <old> <new>

# Commit
git commit -m "message"
git commit -am "message"  # Add and commit tracked files
git commit --amend  # Amend last commit
git commit --amend --no-edit  # Amend without changing message
git commit --allow-empty -m "message"  # Empty commit (useful for triggers)

# View history
git log
git log --oneline
git log --graph --oneline --all --decorate
git log --stat  # Show file statistics
git log --patch  # Show diffs
git log -p -2  # Show last 2 commits with diffs
git log --since="2 weeks ago"
git log --until="2025-01-01"
git log --author="Name"
git log --grep="pattern"
git log -- <file>  # History of specific file
git log --follow <file>  # Follow renames

# Show changes
git diff  # Unstaged changes
git diff --staged  # Staged changes
git diff HEAD  # All changes since last commit
git diff <branch>  # Compare with another branch
git diff <commit1> <commit2>
git diff <commit>  # Changes since specific commit
git diff <branch1>...<branch2>  # Changes between branches

# Show commit details
git show <commit>
git show <commit>:<file>  # Show file at specific commit
```
