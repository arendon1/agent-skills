# ClickUp Manager Skill Walkthrough

I have created the `clickup-manager` skill to allow LLM agents to manage your ClickUp projects using your Personal Access Token.

## Created Files

### [SKILL.md](file:///clickup-manager/SKILL.md)

Defines the skill, usage instructions, and authentication setup.

### [clickup_client.py](file:///clickup-manager/scripts/clickup_client.py)

A Python helper script that interacts with the ClickUp API. It supports:

- Listing teams (workspaces)
- Listing spaces
- Listing folders
- Listing lists
- Creating tasks

### [api.md](file:///clickup-manager/references/api.md)

Reference documentation for the API endpoints used.

### [.env.example](file:///clickup-manager/.env.example)

A template for your `.env` file.

## Setup Instructions

1. **Get your PAT** from ClickUp Settings -> Apps.
2. **Use the template**:
    - Copy `clickup-manager/.env.example` to `.env` (or just add the content to your existing `.env` file).
    - Fill in your token:

    ```bash
    CLICKUP_PAT=pk_your_token_here
    ```

    This ensures your token is kept secure and not committed to version control.

## Efficiency Tips 🚀

To save tokens and reduce costs/latency:

1. **Use Brief Mode**: Add `--format brief` to any list command.

    ```bash
    python scripts/clickup_client.py --format brief list-tasks ...
    ```

2. **Filter First**: Don't fetch all tasks. Use `--status` and `--search`.

    ```bash
    python scripts/clickup_client.py list-tasks --status "Open" --search "fix"
    ```

    python scripts/clickup_client.py list-tasks --status "Open" --search "fix"

    ```

### Scoping & Overrides 🎯

You can set default IDs in `.env` (e.g., `CLICKUP_LIST_ID`) to omit arguments:

```bash
python scripts/clickup_client.py list-tasks
```

**Override**: To check a *different* list or workspace, just provide the argument. It takes precedence over the `.env` variable:

```bash
python scripts/clickup_client.py list-tasks --list-id <DIFFERENT_LIST_ID>
```

## Verification

To verify the skill, set your `CLICKUP_PAT` environment variable and run:

```bash
python clickup-manager/scripts/clickup_client.py list-teams
```
