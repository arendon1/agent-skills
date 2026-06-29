---
name: skill-find
description: |
  Discover external skills from the skills.sh registry. Search by keyword and/or
  GitHub owner, present ranked options with install counts, and recommend. Does NOT
  install — pair with skill-add.
  Use when the user wants to find a skill for a task, or says "find a skill", "is
  there a skill for", "search skills", "browse skills", "what skills exist for".
invocation: auto
layer: utility
metadata:
  version: "1.0.0"
---

# skill-find — discover external skills

Discover external skills from the skills.sh registry. Search by keyword and/or
GitHub owner, present ranked options with install counts, and recommend one. Does
NOT install — pair with the `skill-add` skill to integrate.

## WHEN (self-trigger)

- User queries for an external skill: "find a skill", "is there a skill for",
  "search skills", "browse skills", "what skills exist for".
- The active plan needs a capability none of the repo's skills provide, and an
  external skill might fill the gap.

## HOW IT WORKS

Wraps `npx skills find <query>` so it works whether or not the `skills` package is
installed — `npx` resolves it at runtime.

```
npx skills find <query>                    # search by keyword
npx skills find <query> --owner <owner>    # restrict to a GitHub owner
```

## STEP 0 — SCOPE THE QUERY

Turn the user's request into a search query. Vague "find a skill for testing" ->
"test", "tdd", "testing". Concrete "find a skill for mermaid diagrams" -> "mermaid"
or "diagram". One to three keywords beats a sentence.

## STEP 1 — SEARCH

Run `npx skills find <query>`. If the user named a GitHub owner, add
`--owner <owner>`. Present the results ranked by install count (the CLI shows this).

## STEP 2 — RANK + RECOMMEND

For each result, show:
- **Skill** — `owner/repo@skill-name`
- **Installs** — count (popularity signal)
- **URL** — `skills.sh/owner/repo/skill-name`

Recommend one based on:
- Install count (popularity).
- Description match to the user's need.
- Owner reputation (if known).

Do NOT install. Tell the user: "to integrate, run the `skill-add` skill with
`owner/repo@skill-name`."

## STEP 3 — HAND OFF

If the user picks one, hand to the `skill-add` skill:
```
skill-add owner/repo@skill-name
```

## BOUNDARIES

- MUST NOT install skills. That's `skill-add`'s job.
- MUST use `npx skills find` (works without a global install).
- MUST present install counts so the user can judge popularity.
- MUST recommend one, not just list.
- MUST hand off to `skill-add` for integration.
