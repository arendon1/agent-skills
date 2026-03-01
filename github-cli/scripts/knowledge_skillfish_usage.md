# Technical Knowledge (USAGE): skillfish

> [!NOTE]
> This artifact was generated via `github-cli` deep analysis (Mode: usage).
> It provides actionable expertise for an agent to use the tool.

## 📋 Overview
- **URL**: https://github.com/knoxgraeme/skillfish
- **Description**: The skill manager for AI coding agents. Install, update, and sync skills across Claude Code, Cursor, Copilot + more.
- **Primary Language**: TypeScript
- **Complexity**: 1747KB, 64 nodes

## 🔧 Usage Expertise

### 🕹️ CLI Interface
- Binary: `skillfish`

### 🧩 Public API Surface
- `SKILL_FILENAME`
- `installSkill`
- `detectAgentInProject`
- `API_TIMEOUT_MS`
- `trackCommand`
- `detectAgentGlobally`
- `printBanner`
- `getBannerText`
- `addCommand`
- `detectAgent`
- `getSkillSha`
- `RepoNotFoundError`
- `RateLimitError`
- `getDetectedAgentsForLocation`
- `ERROR_CODES`
- `safeCopyDir`
- `PROJECT_MANIFEST_VERSION`
- `removeCommand`
- `writeProjectManifest`
- `LOGO_LINES`

## 📂 Repository Landmarks
- `README.md`
- `package.json`
- `src/index.ts`

## 📖 Specialized Documentation

## Quick Start


```bash


# One-off skill installation

npx skillfish add owner/repo



# For skill management (list, update, remove), install globally

npm i -g skillfish
```

One command installs to **all detected agents** on your system.

> [!TIP]
> **New:** [Sync skills across your team](#team-skill-sync) with `skillfish bundle`.



## Examples


```bash
skillfish add owner/repo             # Install from a repository
skillfish add owner/repo --all       # Install all skills from repo
skillfish init                       # Create a new skill (interactive)
skillfish init --name my-skill       # Create with a specified name
skillfish list                       # See what's installed
skillfish search github              # Search for skills
skillfish update                     # Update all skills
skillfish remove old-skill           # Remove a skill
skillfish submit owner/repo          # Submit your skills to skill.fish
skillfish bundle                     # Create skillfish.json from installed skills
skillfish install                    # Sync skills from manifest
skillfish install --dry-run          # Preview what would change
```



### install


Install skills from a `skillfish.json` manifest.

```bash
skillfish install                    # Install from manifest (auto-detects location)
skillfish install --project          # Install from ./skillfish.json
skillfish install --global           # Install from ~/skillfish.json
skillfish install --dry-run          # Preview changes without installing
skillfish install --yes              # Skip confirmation prompts
```

When a skill is removed from the manifest, `skillfish install` removes it from your system. Manually installed skills are never removed automatically.



### CI example


```bash


# Install skills in CI (non-interactive, JSON output)

skillfish add owner/repo --yes --json


