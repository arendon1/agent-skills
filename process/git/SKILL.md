---
name: git
description: |
  Proactive version control. Creates worktrees for plan work, commits at
  checkpoints with conventional commits, merges at plan completion, resolves
  conflicts safely.
  Use when starting a session, hitting a plan checkpoint, or finishing a branch,
  or when the user says "commit", "checkpoint", "merge", "branch", "worktree",
  "resolve conflict".
invocation: auto
layer: process
metadata:
  version: "1.0.0"
---

# git — proactive version control

Proactive version control for plan work. Creates an isolated workspace per plan,
commits at checkpoints with conventional commits, merges at plan completion, and
resolves conflicts safely by preserving both intents.

## WHEN (self-trigger)

- Session start before plan work (create or verify isolation).
- A plan checkpoint (after each `PLAN.md` task flips to `[x]`).
- Plan completion (merge or PR).
- A merge/rebase conflict occurs.
- User says "commit", "checkpoint", "merge", "branch", "worktree", "resolve
  conflict".

## STEP 0 — DETECT EXISTING ISOLATION

Before creating anything, check whether you are already in an isolated workspace:

```
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

**Submodule guard:** `GIT_DIR != GIT_COMMON` is also true inside submodules. Verify
you are not in a submodule:

```
git rev-parse --show-superproject-working-tree 2>/dev/null
```

If already in a linked worktree (and not a submodule): skip to the operation you
need (commit / merge / resolve). Do NOT create another worktree.

If in a normal repo checkout: ask for consent before creating a worktree, unless
the user has already declared a preference. Honor any declared preference without
asking. If the user declines, work in place.

## STEP 1 — CREATE ISOLATED WORKSPACE (when starting plan work)

Prefer the harness's native worktree tool if one exists (it handles placement,
branch creation, and cleanup automatically). If no native tool is available, fall
back to `git worktree add`:

- Branch name from the plan slug: `docs/plans/2026-06-28-feature-oauth-flow` ->
  branch `feature-oauth-flow`.
- Place the worktree in the project's conventional worktree directory, or a sibling
  dir. Explicit user preference always beats observed filesystem state.

Never fight the harness — if a native tool exists, use it. `git worktree add`
when a native tool exists creates phantom state the harness can't manage.

## STEP 2 — COMMIT AT CHECKPOINTS

After each `PLAN.md` task flips to `[x]` (the `build` loop triggers this), commit:

- Stage the task's files (code + tests + any artifact edits).
- Conventional commit message: `T<n>: <goal line>` + `§V` cites. Example:
  `T3: add auth middleware (V1, I.api)`.
- One commit per task. Small, reviewable, in dependency order.

NEVER start implementation work on the default branch (main/master) without
explicit user consent.

## STEP 3 — FINISH A DEVELOPMENT BRANCH

Before presenting options, verify the build:

- Run the project's test suite. If failing, stop — must fix before completing.
- Run the `verify` discipline on the whole plan.

Then detect the workspace state (normal repo vs linked worktree, named branch vs
detached HEAD) and present structured options:

1. **Merge to base** — fast-forward if possible, else a merge commit. Then delete
   the branch (and remove the worktree if linked).
2. **Open a PR** — push the branch, open a pull request against the base branch.
3. **Keep the branch** — leave it for later; report the branch name + worktree path.
4. **Abort / discard** — only with explicit confirmation; deletes the branch and
   worktree.

For a detached-HEAD worktree (externally managed), present the reduced 3-option
menu (no merge — the harness manages it).

Determine the base branch: `git merge-base HEAD main` or `master`, or ask the user.

## STEP 4 — RESOLVE MERGE/REBASE CONFLICTS

When a merge or rebase conflict occurs:

1. **See the current state** — git history and the conflicting files.
2. **Find the primary sources** for each conflict. Understand deeply why each
   change was made and the original intent. Read commit messages, PRs, original
   issues/tickets.
3. **Resolve each hunk.** Preserve both intents where possible. Where
   incompatible, pick the one matching the merge's stated goal and note the
   trade-off. Do NOT invent new behavior. ALWAYS resolve; NEVER `--abort`.
4. **Discover the project's automated checks** and run them — typically typecheck,
   then tests, then format. Fix anything the merge broke (invoke `debug` if a test
   failure is non-trivial; invoke `lessons` if it reveals an invariant gap).
5. **Finish the merge/rebase.** Stage everything and commit. If rebasing, continue
   until all commits are rebased.

## COMMIT CONVENTIONS

Conventional commits (§14). Normal English (not caveman) for commit messages:

```
feat(auth): add token expiry check middleware
fix(refund): use <= not < for token expiry comparison (B1, V2)
refactor(validation): extract middleware, no behavior change
test(auth): add TestV2_TokenExpiryRejected
docs(spec): update §V.2 invariant
chore(deps): bump jose to 5.4.0
perf(cache): memoize auth check
ci(deploy): add staging job
```

Plan-task checkpoints: `T<n>: <goal line> (<§V cites>)`.

## BOUNDARIES

- MUST detect existing isolation before creating a worktree.
- MUST prefer native worktree tools over `git worktree add`.
- MUST NEVER start implementation on main/master without explicit consent.
- MUST commit after each `PLAN.md` task (conventional commits).
- MUST verify tests before finishing a branch (via the `verify` discipline).
- MUST NEVER `--abort` a merge; always resolve, preserving both intents.
- MUST NOT invent new behavior during conflict resolution.
- MUST use conventional commits in normal English.
