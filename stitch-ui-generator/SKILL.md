---
name: stitch-ui-generator
description: >-
  Enables UI generation using Google Stitch API for local development.
  Focuses on HTML, CSS, and jQuery archetypes.
  Requires a GOOGLE_STITCH_API_KEY in the workspace root /.env file.
  Mandates a human-in-the-loop workflow (/app-generate-ui).
---

# 🎨 Stitch UI Generator

This skill enables AI agents to leverage the Google Stitch API to generate highly detailed and finely-tuned UI components for local development. It prioritizes simple technologies (HTML/CSS/jQuery) and follows a rigorous human-in-the-loop workflow.

## 🚀 Usage

Trigger the main workflow by typing:
`@stitch-ui-generator /app-generate-ui`

## 🛠️ Tools

### `validate_environment`

Runs `scripts/validate_env.py` to ensure the `GOOGLE_STITCH_API_KEY` is present in the root `.env` file.

### `call_stitch_api`

Runs `scripts/stitch_client.py` to send a prompt to Google Stitch and retrieve the generated code.
**Params:**

- `prompt`: The detailed UI generation prompt.
- `tech_stack`: (Optional) Defaults to "jquery".

### `validate_generated_code`

Runs `scripts/validate_ui.py` to check for HTML syntax errors and basic jQuery validity before presenting to the user.

## 🧠 Context Engineering Integration

When crafting prompts for Google Stitch, always:

1. Load `references/prompt_templates.md`.
2. Apply principles from `@context-engineer` (Signal-to-Noise, Progressive Disclosure).
3. Specify the project structure to ensure styles and scripts are correctly linked.

## 🛡️ Safety Guardrails

- **Key Safety:** Never log or display the `GOOGLE_STITCH_API_KEY`.
- **Path Safety:** Scripts use absolute paths to reconcile workspace locations.
- **Deterministic Check:** Always run `validate_generated_code` before saving files.
