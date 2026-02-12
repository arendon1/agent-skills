---
name: git-master
description: "Complete Git expertise system for ALL git operations. PROACTIVELY activate for: (1) ANY Git task (basic/advanced/dangerous), (2) Repository management, (3) Branch strategies and workflows, (4) Conflict resolution, (5) History rewriting/recovery. Provides expert guidance, safety guardrails, and platform best practices."
---

# Git Master

Expert Git operations with built-in safety rails and best practices.

## 🚨 CRITICAL RULES

1.  **Safety First**: Before ANY destructive operation (`reset --hard`, `force push`, `filter-repo`), you MUST:
    *   Explicitly warn the user.
    *   Offer to create a backup branch.
    *   Ask for confirmation.
2.  **User Preference**: At the start of a task, ask: "Do you want automatic commits or manual control?"
3.  **Windows Paths**: Always use backslashes (`\`) for file paths in Windows environments.

## 📚 References

Load these specific references based on the valid user task:

| Topic | Reference File |
| :--- | :--- |
| **Basics** | `references/basic-operations.md` |
| **Branch/Merge** | `references/branching-merging.md` |
| **Remotes** | `references/remote-operations.md` |
| **Advanced** | `references/advanced-operations.md` |
| **Platforms** | `references/platform-guide.md` |

## 🛠️ Quick Reference

### Safety Check Pattern
```bash
# Before dangerous ops
git status
git branch backup-$(date +%Y%m%d-%H%M%S)
# Proceed only after confirmation
```

### Most Common Operations

**Status & Log**
```bash
git status
git log --oneline --graph --all
```

**Undo Last Commit (Keep Changes)**
```bash
git reset --soft HEAD~1
```

**Emergency Recovery**
```bash
git reflog
# Find the hash before the mistake, then:
# git reset --hard <hash> (if local)
# git cherry-pick <hash> (to recover specific commit)
```

## 🔍 When to Use

*   **Repository Setup**: Init, clone, config.
*   **Daily Work**: Commit, push, pull, branch, merge.
*   **Fixing Issues**: Conflicts, detached HEAD, wrong branch.
*   **Advanced**: Interactive rebase, stash, submodules, worktrees.
*   **Disaster Recovery**: Reflog, fsck, filter-repo.
