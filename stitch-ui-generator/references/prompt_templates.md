# Stitch Prompt Templates

Use these templates to maximize the "Signal-to-Noise" ratio for Google Stitch.

## 🛠️ Template: Component with jQuery Logic

**Intent:** Use when building interactive widgets (modals, tabs, dropdowns).

```text
ACT AS: Google Stitch UI Architect
CONTEXT: Designing a [COMPONENT_NAME] for a local project.
CONSTRAINTS: 
- Use HTML5 semantic tags.
- Use Vanilla CSS for layout (Flex/Grid).
- Use jQuery [VERSION] for DOM manipulation.
- Avoid external CDNs unless specified (prefer relative paths like ./js/jquery.min.js).

LAYOUT PLAN:
1. [LAYOUT_STEP_1]
2. [LAYOUT_STEP_2]

INTERACTION DESIGN:
- [EVENT]: [ACTION] using jQuery.

OUTPUT: Return only the complete HTML code with embedded CSS and JS for preview.
```

## 📄 Template: Full Responsive Page

**Intent:** Use when building a landing page or dashboard.

```text
ACT AS: Google Stitch UI Architect
CONTEXT: Full-page layout for [APP_NAME].
STYLE GUIDE: [COLORS/THEME/FONT]
STRUCTURE:
- Header: [DESCRIPTION]
- Main: [DESCRIPTION]
- Footer: [DESCRIPTION]

TECH STACK: HTML5, jQuery, CSS Variables.
```

## 🧬 Context Engineering Tips for Stitch

1. **Be Deterministic:** Don't say "Make it look good." Say "Use 16px border-radius and #2D3436 for the background."
2. **Modularize:** Ask for the CSS in a `<style>` block and JS in a `<script>` block for easy extraction.
3. **Reference Local Assets:** If the project has an `assets/` folder, tell Stitch to use those paths.
