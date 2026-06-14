# Branching and Merging

## Branch Management

### Creating and Switching Branches

```bash
# List branches
git branch  # Local branches
git branch -r  # Remote branches
git branch -a  # All branches
git branch -v  # With last commit info
git branch -vv  # With tracking info

# Create branch
git branch <branch-name>
git branch <branch-name> <start-point>  # From specific commit/tag

# Switch branch
git switch <branch-name>
git checkout <branch-name>  # Old syntax, still works

# Create and switch
git switch -c <branch-name>
git checkout -b <branch-name>
git switch -c <branch-name> <start-point>

# Delete branch
git branch -d <branch-name>  # Safe delete (only if merged)
git branch -D <branch-name>  # Force delete (even if not merged)

# Rename branch
git branch -m <old-name> <new-name>
git branch -m <new-name>  # Rename current branch

# Set upstream tracking
git branch --set-upstream-to=origin/<branch>
git branch -u origin/<branch>
```

### Branch Strategies

**Git Flow:**
- `main/master`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: New features
- `release/*`: Release preparation
- `hotfix/*`: Production fixes

**GitHub Flow:**
- `main`: Always deployable
- `feature/*`: Short-lived feature branches
- Create PR, review, merge

**Trunk-Based Development:**
- `main`: Single branch
- Short-lived feature branches (< 1 day)
- Feature flags for incomplete features

**GitLab Flow:**
- Environment branches: `production`, `staging`, `main`
- Feature branches merge to `main`
- Deploy from environment branches

## Merging and Rebasing

### Merge Strategies

```bash
# Fast-forward merge (default if possible)
git merge <branch>

# Force merge commit (even if fast-forward possible)
git merge --no-ff <branch>

# Squash merge (combine all commits into one)
git merge --squash <branch>
# Then commit manually: git commit -m "Merged feature X"

# Merge with specific strategy
git merge -s recursive <branch>  # Default strategy
git merge -s ours <branch>  # Always use "our" version
git merge -s theirs <branch>  # Always use "their" version (requires merge-theirs)
git merge -s octopus <branch1> <branch2> <branch3>  # Merge multiple branches

# Merge with strategy options
git merge -X ours <branch>  # Prefer "our" changes in conflicts
git merge -X theirs <branch>  # Prefer "their" changes in conflicts
git merge -X ignore-all-space <branch>
git merge -X ignore-space-change <branch>

# Abort merge
git merge --abort

# Continue after resolving conflicts
git merge --continue
```

### Conflict Resolution

```bash
# When merge conflicts occur
git status  # See conflicted files

# Conflict markers in files:
# <<<<<<< HEAD
# Your changes
# =======
# Their changes
# >>>>>>> branch-name

# Resolve conflicts manually, then:
git add <resolved-file>
git commit  # Complete the merge

# Use mergetool
git mergetool

# Accept one side completely
git checkout --ours <file>  # Keep our version
git checkout --theirs <file>  # Keep their version
git add <file>

# View conflict diff
git diff  # Show conflicts
git diff --ours  # Compare with our version
git diff --theirs  # Compare with their version
git diff --base  # Compare with base version

# List conflicts
git diff --name-only --diff-filter=U
```

### Rebase Operations

**⚠️  WARNING: Rebase rewrites history. Never rebase commits that have been pushed to shared branches!**

```bash
# Basic rebase
git rebase <base-branch>
git rebase origin/main

# Interactive rebase (POWERFUL)
git rebase -i <base-commit>
git rebase -i HEAD~5  # Last 5 commits

# Interactive rebase commands:
# p, pick = use commit
# r, reword = use commit, but edit message
# e, edit = use commit, but stop for amending
# s, squash = use commit, but meld into previous commit
# f, fixup = like squash, but discard commit message
# x, exec = run command (rest of line) using shell
# b, break = stop here (continue rebase later with 'git rebase --continue')
# d, drop = remove commit
# l, label = label current HEAD with a name
# t, reset = reset HEAD to a label

# Rebase onto different base
git rebase --onto <new-base> <old-base> <branch>

# Continue after resolving conflicts
git rebase --continue

# Skip current commit
git rebase --skip

# Abort rebase
git rebase --abort

# Preserve merge commits
git rebase --preserve-merges <base>  # Deprecated
git rebase --rebase-merges <base>  # Modern approach

# Autosquash (with fixup commits)
git commit --fixup <commit>
git rebase -i --autosquash <base>
```

### Cherry-Pick

```bash
# Apply specific commit to current branch
git cherry-pick <commit>

# Cherry-pick multiple commits
git cherry-pick <commit1> <commit2>
git cherry-pick <commit1>..<commit5>

# Cherry-pick without committing
git cherry-pick -n <commit>
git cherry-pick --no-commit <commit>

# Continue after resolving conflicts
git cherry-pick --continue

# Abort cherry-pick
git cherry-pick --abort
```
