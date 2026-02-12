# Remote Operations

## Remote Management

```bash
# List remotes
git remote
git remote -v  # With URLs

# Add remote
git remote add <name> <url>
git remote add origin https://github.com/user/repo.git

# Change remote URL
git remote set-url <name> <new-url>

# Remove remote
git remote remove <name>
git remote rm <name>

# Rename remote
git remote rename <old> <new>

# Show remote info
git remote show <name>
git remote show origin

# Prune stale remote branches
git remote prune origin
git fetch --prune
```

## Fetch and Pull

```bash
# Fetch from remote (doesn't merge)
git fetch
git fetch origin
git fetch --all  # All remotes
git fetch --prune  # Remove stale remote-tracking branches

# Pull (fetch + merge)
git pull
git pull origin <branch>
git pull --rebase  # Fetch + rebase instead of merge
git pull --no-ff  # Always create merge commit
git pull --ff-only  # Only if fast-forward possible

# Set default pull behavior
git config --global pull.rebase true  # Always rebase
git config --global pull.ff only  # Only fast-forward
```

## Push

```bash
# Push to remote
git push
git push origin <branch>
git push origin <local-branch>:<remote-branch>

# Push new branch and set upstream
git push -u origin <branch>
git push --set-upstream origin <branch>

# Push all branches
git push --all

# Push tags
git push --tags
git push origin <tag-name>

# Delete remote branch
git push origin --delete <branch>
git push origin :<branch>  # Old syntax

# Delete remote tag
git push origin --delete <tag>
git push origin :refs/tags/<tag>

# ⚠️ DANGEROUS: Force push (overwrites remote history)
# ALWAYS ASK USER FOR CONFIRMATION FIRST
git push --force
git push -f

# ⚠️ SAFER: Force push with lease (fails if remote updated)
git push --force-with-lease
git push --force-with-lease=<ref>:<expected-value>
```

**Force Push Safety Protocol:**

Before ANY force push, execute this safety check:

```bash
echo "⚠️  DANGER: Force push will overwrite remote history!"
echo ""
echo "Remote branch status:"
git fetch origin
git log --oneline origin/<branch> ^<branch> --decorate

if [ -z "$(git log --oneline origin/<branch> ^<branch>)" ]; then
    echo "✓ No commits will be lost (remote is behind local)"
else
    echo "❌ WARNING: Remote has commits that will be LOST:"
    git log --oneline --decorate origin/<branch> ^<branch>
    echo ""
    echo "These commits from other developers will be destroyed!"
fi

echo ""
echo "Consider using --force-with-lease instead of --force"
echo ""
read -p "Type 'force push' to confirm: " confirm
if [[ "$confirm" != "force push" ]]; then
    echo "Cancelled."
    exit 1
fi
```
