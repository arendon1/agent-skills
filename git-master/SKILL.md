---
name: git-master
description: >-
  Proactive version control strategy for AI agents. Creates worktrees, commits at plan
  checkpoints with conventional commits, merges at plan completion. Load at session start
  and keep in context permanently.
license: Apache-2.0
metadata:
  version: "2.0.0"
  language: en
  trit: -1
  author: agent-builder
---

# Git Master v2

Proactive, checkpoint-driven version control. Git-master loads at session start and stays
in context permanently. The agent commits autonomously at every meaningful milestone
defined by its plan.

## Core Philosophy

- Commit is a checkpoint, not a release.
- Every completed step in the plan is a commit.
- Worktrees isolate work, never touch `main` directly.
- The agent drives git — the user never has to ask.

## Workflow

### Session Start

1. **Check branch.** If not on `main` (or `master`), ask the user which branch to use as
   base. Never assume.
2. **Check for pre-existing changes.** If the working tree has unstaged/staged changes
   from before the session, commit them as step 0. Infer intent from the diff for the
   commit message.
3. **Check for stash.** Ignore it. Stash is the user's problem.
4. **Handle dirty `main`.** If `main` has uncommitted changes when creating a worktree:

   ```bash
   git stash push -m "git-master: pre-worktree stash"
   git worktree add ../wt/<scope>/<desc> -b wt/<scope>/<desc>
   git stash pop  # back in the original workspace, not the worktree
   ```

5. **Create worktree.** One worktree per plan, never on `main`.

   ```bash
   git worktree add ../wt/<scope>/<desc> -b wt/<scope>/<desc>
   ```

   Navigate into the worktree. All work happens there.

### Naming Convention

```
wt/<scope>/<short-description>
```

- Derive `<scope>` and `<description>` from the plan. Example:
  `wt/fix/auth-token-expiry`, `wt/feat/user-onboarding`
- If no plan exists yet (ad-hoc work), fallback to:
  `wt/agente-<topic>` (e.g., `wt/agente-exploracion-api`).

### During the Plan

For every step in the plan:

1. **Work on the step.**
2. **Announce completion:** `✅ <step description> done.`
3. **Decide whether to commit:**
   - **Skip commit** if the step produced only trivial changes: renaming a variable,
     changing a string literal, cosmetic formatting.
   - **Commit** for everything else.
4. **Commit:**

   ```bash
   git add -A
   git commit -m "<type>[(<scope>)]: <description>"
   ```

   **Conventional commit format:**
   - `<type>`: `feat`, `fix`, `refactor`, `chore`, `test`, `docs`, `perf`, `ci`,
     `style`. Infer from the plan step.
   - `<scope>`: optional, inferred from the module/area touched.
   - `<description>`: imperative, concise, derived from the plan step.

   Examples:
   - Plan step "Add JWT refresh endpoint" → `feat(auth): add JWT refresh endpoint`
   - Plan step "Fix pagination off-by-one" → `fix(api): correct pagination off-by-one`
   - Plan step "Extract validation middleware" → `refactor: extract validation middleware`

5. **Pre-commit gate:** Before committing, run the project's test and lint scripts if
   they exist (`npm test`, `npm run lint`, `pytest`, `cargo test`, etc.).
   - If they pass → proceed with commit.
   - If they fail → attempt 1 fix loop, then re-run. If they fail again → report to user,
     do not commit.
6. **Proceed to next step.**

**Multiple commits per step:** Only if the step touches two clearly disconnected areas.
Example: fixing a bug in `auth.ts` and a separate typo in `README.md` → two commits.

**No amend period.** Never `git commit --amend`. Always create a new commit for
corrections.

### High-Risk Detection

Steps matching these heuristics are flagged as high-risk and receive granular commits:

- Touches database migrations, schemas, or seed data
- Touches authentication, authorization, or security code
- Touches CI/CD pipelines, deployment configs, or infrastructure
- Touches configuration files that affect production behavior
- Touches payment, billing, or financial code
- Touches `DROP`, `DELETE`, `TRUNCATE` operations or destructive data changes

**High-risk commit strategy:** Commit per file or logical group within the step. Do not
wait for step completion.

```
Step: "Migrate user schema and update related entities"
  → commit 1: "refactor(db): add migration for user schema changes"
  → commit 2: "refactor(models): update User entity for new schema"
  → commit 3: "test(db): update user-related tests"
✅ Step complete.
```

### Plan Interruption

If the user changes direction mid-plan ("do Z instead of Y"):

1. Ask: "Current worktree has uncommitted changes. Commit and close, or discard?"
2. Follow the chosen path:
   - **Commit:** commit current state, merge, clean up, create new worktree.
   - **Discard:** remove worktree, create new worktree from scratch.

### Plan Completion

When all steps are done:

1. **Rebase on base branch** (if it advanced since worktree creation):

   ```bash
   git fetch origin
   git rebase origin/main  # or the base branch
   ```

   If rebase fails due to conflicts, resolve automatically preferring worktree version
   (`git checkout --ours`). If unresolvable, pause and ask for help.

2. **Merge into base branch:**

   ```bash
   git checkout main  # or the base branch
   git merge wt/<scope>/<desc>
   ```

   If merge conflicts: auto-resolve preferring worktree version. If unresolvable, pause
   and ask for help.

3. **Push:**

   ```bash
   git push origin main  # or the base branch
   ```

4. **Clean up:**
   - Remove the worktree: `git worktree remove ../wt/<scope>/<desc> --force`
   - Keep the branch: do not delete `wt/<scope>/<desc>`. It stays for reference.

### Read-Only Sessions

If the plan is purely research (reading docs, searching code, no changes expected):
do not create a worktree. Do not commit. Just report findings.

## Safety Rules

### Before ANY destructive operation

(`reset --hard`, `force push`, `filter-repo`, `clean -fd`):

1. Explicitly warn the user.
2. Offer to create a backup branch.
3. Ask for confirmation.

### No amend period

Never rewrite history with `--amend`. Always new commits.

### No merge commits on main without rebase

Always rebase the worktree branch onto the latest base before merging. This keeps
history linear and avoids surprise conflicts from concurrent work.

### No tags

Tags are the user's decision. Never create tags automatically.

### Multiple worktrees

If multiple agents produce worktrees simultaneously, each one rebases on the latest
base branch before merging. Last one to merge handles the rebase.

## Reference

The `references/` directory contains command-level documentation. Load as needed:

| Topic | File |
|-------|------|
| Basic operations | `references/basic-operations.md` |
| Branching & merging | `references/branching-merging.md` |
| Remote operations | `references/remote-operations.md` |
| Advanced operations | `references/advanced-operations.md` |
| Platform guides | `references/platform-guide.md` |
