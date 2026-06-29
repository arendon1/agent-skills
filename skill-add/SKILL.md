---
name: skill-add
description: |
  Integrate an external skill into this repo. Fetch via npx skills add, audit against
  the constitution with skill-forge, place with upstream license attribution, and
  report incompatibilities. Use when adding an external skill, after skill-find picks
  one, or when the user names a source to add.
  Use when the user says "add this skill", "install skill", "integrate skill", "pull
  in skill", "skill-add", or names a source to add.
invocation: auto
layer: utility
metadata:
  version: "1.0.0"
---

# skill-add — integrate an external skill

Integrate an external skill into this repo. Fetch it via `npx skills add`, audit it
against the constitution (`AGENTS.md`) with `skill-forge audit`, place it with
upstream license attribution, and report any incompatibilities.

## WHEN (self-trigger)

- User chooses to integrate an external skill (after `skill-find` picked one).
- User says "add this skill", "install skill", "integrate skill", "pull in skill",
  "skill-add", or names a source (`owner/repo@skill-name` or a URL).

## HOW IT WORKS

Two stages: fetch with `npx skills add`, then audit with `skill-forge`. The fetch
works whether or not the `skills` package is installed — `npx` resolves it at
runtime. The audit enforces the constitution directly (exit 0 = PASS).

## STEP 0 — PARSE THE SOURCE

Accept the source in any of these forms:
- `owner/repo@skill-name` (skills.sh format)
- `owner/repo` (whole repo)
- A GitHub URL

Extract the skill name for the target directory.

## STEP 1 — FETCH

Fetch the skill into the repo (project-level, not global):

```
npx skills add <source> --skill <skill-name> -a '*' -y
```

Flags:
- `--skill <name>` — install a specific skill (or `*` for all).
- `-a '*'` — install to all agents.
- `-y` — skip confirmation prompts.
- `--copy` — copy files instead of symlinking (preferred for a repo we control).

If the fetch fails (network, not found), report the error and stop. Do NOT guess a
different source.

## STEP 2 — PLACE + ATTRIBUTE

The skill lands in the repo's skill directory. Ensure:
- The skill has its own directory at the repo root (matching §2 discovery).
- Upstream license attribution is preserved (keep the upstream `LICENSE` or add a
  `LICENSE-upstream` note if the repo's license differs). NEVER strip attribution.
- The skill's `name:` frontmatter matches its directory name.

## STEP 3 — AUDIT

Run the constitution enforcer on the new skill:

```
python skill-forge/scripts/audit.py <skill-name>
```

### If PASS

The skill is integrated. Regenerate the manifest:
```
python skill-forge/scripts/manifest.py
```
Commit: `feat(<skill>): integrate external skill <source>`.

### If FAIL

Report every failing check (missing `invocation`/`layer`, harness names in body,
missing `Use when`, over 500 lines, etc.). Two options:
- **Fixable** — migrate the frontmatter (add `invocation`/`layer`/`provides`/
  `loop`/`deliverable`), reword harness-specific body text to abstract behavior,
  trim to 500 lines. This is a frontmatter/wording migration, not a logic rewrite.
- **Not fixable without rewriting** — report the incompatibility and ask the user
  whether to fork-and-rewrite or reject. Do NOT merge a skill that fails audit.

## STEP 4 — REPORT

End with a compact report (caveman):

```
skill-add <source>:
- fetch:     PASS (N files, <dir>/)
- license:   PASS (upstream <license> preserved)
- audit:     PASS | FAIL (<n> errors)
- manifest:  regenerated
- commit:    <hash> | blocked (audit FAIL)
```

## BOUNDARIES

- MUST fetch via `npx skills add` (works without a global install).
- MUST preserve upstream license attribution. NEVER strip it.
- MUST audit with `skill-forge` after fetching. NEVER merge a failing skill.
- MUST regenerate the manifest after a successful integration.
- MUST report incompatibilities honestly — do not weaken the audit to pass a skill.
- MUST use `--copy` for a repo we control (avoids symlink drift).
