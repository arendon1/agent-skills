---
description: Interactive UI generation workflow with human-in-the-loop approval.
---

# 🚀 App UI Generation Workflow

// turbo-all

1. **Information Gathering**
   - Ask the user what UI component or screen they want to build.
   - Clarify the structure: "A single HTML file, or separate .html, .css, .js files?"
   - Confirm the tech stack (defaulting to HTML5 + jQuery).

2. **Architecture Planning**
   - Review current project files to ensure alignment.
   - Present a **Markdown Plan** describing:
     - **Layout:** (e.g., Responsive Grid, Flexbox Sidebar).
     - **Functionality:** (e.g., "jQuery for tab switching").
     - **Theme:** (e.g., Dark mode, specific brand colors).
   - **WAIT for user approval** before proceeding.

3. **Prompt Engineering**
   - Use `@context-engineer` principles to craft a high-signal prompt.
   - Reference `references/prompt_templates.md` for the best Stitch-compatible format.

4. **API Execution**
   - Run `scripts/validate_env.py` to ensure the API key is ready.
   - Run `scripts/stitch_client.py` with the crafted prompt.

5. **Validation & Staging**
   - Run `scripts/validate_ui.py` on the returned code.
   - Present the code to the user in a formatted block.
   - **WAIT for user final approval**.

6. **File Integration**
   - After user confirms, write the code to the appropriate files in the local directory.
   - Verify the files exist and are readable.
