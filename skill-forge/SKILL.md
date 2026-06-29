---
name: skill-forge
description: |
  Constitution enforcer. Scaffolds new skills and validates them against AGENTS.md.
  Use when creating a new skill, auditing an existing skill for compliance, or
  migrating a skill to the new frontmatter schema.
invocation: auto
layer: utility
metadata:
  version: "2.0.0"
---

# skill-forge — constitution enforcer

Layer 0/3 utility. Scaffolds new skills (`init`) and directly validates existing
skills against the constitution (`audit`). Generates the harness-discovery
manifest by layer (`manifest`).

This skill IS the constitution's enforcement arm. Every other skill in the repo
MUST pass `audit`. The frontmatter schema, layer rules, triggering contracts,
agnosticism guardrails, and size limit live in `AGENTS.md` (§5, §3, §4, §9, §15)
and are enforced here.

## WHEN (self-trigger)

- Creating a new skill.
- Auditing an existing skill for structural / compliance issues.
- Migrating a skill to the new frontmatter schema.
- A skill was added, renamed, or moved (regenerate the manifest).

## COMMANDS

```
# Scaffold a new skill with constitution-compliant frontmatter
python skill-forge/scripts/init.py <name>
python skill-forge/scripts/init.py grill --invocation user --layer process \
    --loop grill --deliverable "PRD.md + plan folder"
python skill-forge/scripts/use-clickup --layer domain --provides clickup-api

# Validate a skill (exit 0 = PASS, 1 = FAIL)
python skill-forge/scripts/audit.py <name>
python skill-forge/scripts/audit.py <name> --strict   # warnings -> failures

# Generate the harness-discovery manifest, grouped by layer
python skill-forge/scripts/manifest.py                 # write .claude-plugin/marketplace.json
python skill-forge/scripts/manifest.py --check         # fail if stale
python skill-forge/scripts/manifest.py --print         # stdout only
```

## WHAT AUDIT ENFORCES

| Check | Severity | Rule |
|---|---|---|
| frontmatter present | FAIL | `---` block opens `SKILL.md` |
| `name` | FAIL | present, lowercase-hyphens, matches dir name |
| `description` + `Use when` | FAIL | contains `Use when` (or `Usa cuando`) |
| `invocation` | FAIL | one of `auto` / `user` / `bootstrap` |
| `layer` | FAIL | one of `process` / `domain` / `utility` |
| `loop` + `deliverable` | FAIL | required when `invocation: user` |
| `bootstrap` reserved | FAIL | only the `bootstrap` skill may use `invocation: bootstrap` |
| size | FAIL | `SKILL.md` <= 500 lines |
| agnosticism (§9) | FAIL | no harness names or tool APIs in body (list in AGENTS.md §9) |
| slash-command syntax | WARN | use prose `run the X loop`, not a bare slash token |
| `provides` on domain | WARN | `layer: domain` should list capabilities |
| `language` | WARN | `en-US` or `es-CO` if declared |

**Agnosticism note:** harness names are matched as whole words (word boundaries on
both sides), so a generic substring like the one inside `api` does not trigger a
false positive. Tool APIs are matched as standalone tokens.

## THE MANIFEST (generated, never hand-edited)

`.claude-plugin/marketplace.json` is read by the `skills` CLI (`npx skills
list` / `find`) and surfaces our skills grouped by layer. It is a **build
artifact**: the filesystem + `layer:` frontmatter field is the single source of
truth (AGENTS.md §2 — never hardcode a skill list). Regenerate whenever a skill
is added/renamed/moved. `manifest.py --check` fails if the tracked manifest is
stale — wire it into CI or pre-commit.

Format (generated; do not hand-edit):
```json
{
  "metadata": { "pluginRoot": "." },
  "plugins": [
    { "name": "process", "source": ".", "skills": ["<skill-path>", "..."] },
    { "name": "domain",  "source": ".", "skills": ["<skill-path>"] },
    { "name": "utility", "source": ".", "skills": ["<skill-path>"] }
  ]
}
```

## WHY DIRECT VALIDATION (not prompt-output)

The prior `audit.py` emitted an XML prompt for an agent to run checks. That made
compliance non-deterministic and un-scriptable. This version validates directly:
parse frontmatter, check fields, scan body, exit 0/1. CI-friendly, repeatable,
no model in the loop.

## RIGHT-SIZE

A new skill scaffolds with `init`, gets its `description` polished, then runs
`audit` until PASS. A failing audit is never ignored — fix the skill (or the
constitution if the rule is wrong), don't weaken the audit.
