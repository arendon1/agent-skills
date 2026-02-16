---
name: scientific-schematics
description: >-
  Advanced scientific diagram generator with AI-native iterative refinement.
  Includes a Hybrid Rendering Fallback (SVG/PNG) for non-visual environments (VS Code/Copilot).
  Integrates @context-engineer logic for high-fidelity technical visualization.
license: Apache-2.0
metadata:
  version: "2.3.0"
  author: Antigravity
allowed-tools: [generate_image, view_file, list_dir, write_to_file, run_command]
---

# Scientific Schematics (Hybrid-Native)

**Expert-level scientific visualization with universal fallback automation.**

## 🧠 Brain-Power: @context-engineer Integration

This skill applies "Signal-to-Noise" engineering to all diagrams:

1. **Prompt Sharpening**: Structured manifests for `generate_image`.
2. **Logic-First Fallback**: If pixels aren't an option, we use **Structural Code** (Mermaid/SVG).

## 🔄 The Master Workflow (Interactive)

### Case A: Native Environment (Antigravity with Tools)

1. **Generate**: I use `generate_image` for a high-fidelity proposal.
2. **Audit**: Supervisor-eval against 4 dimensions (Accuracy, Clarity, Labels, Geometry).
3. **Refine**: Auto-correction for scores < 8.5 (Journal).
4. **Hito de Decisión**: Presentation to User for approval.

### Case B: Fallback Environment (VS Code / Copilot / CLI)

When visual tools are absent or Mermaid is preferred:

1. **Mermaid Coding**: I generate valid Mermaid.js code with academic themes.
2. **Shadow Pipeline (Zero-Configuration Rendering)**:
    * I save the code to `figures/[name].mmd`.
    * **Auto-Render**: I attempt to run `npx @mermaid-js/mermaid-cli` to generate **SVG** and **PNG** files automatically.
    * **Organization**: Everything is organized in a centralized `figures/` directory within your workspace.
3. **Manual Verification**: If Node/Npx is missing, I guide you to use VS Code's native Mermaid preview.

## 🏢 Workspace Organization

All outputs follow this structure:

```text
workspace/
├── figures/                # Centralized directory for visuals
│   ├── [name].mmd          # Source Mermaid code
│   ├── [name].svg          # Vector output (for Journals)
│   ├── [name].png          # Raster output (for Presentations)
│   └── [name]_log.json     # Review & Metadata log
```

## 📊 Document Quality Standards

| Type | Target Score | Logic |
| :--- | :--- | :--- |
| **Journal** | 8.5+ | Peer-review ready. SVG preferred. High accuracy. |
| **Conference** | 8.0+ | High clarity, transparent PNGs, professional palette. |
| **Poster** | 7.0+ | Visual impact and readability at scale. |
| **Presentation** | 6.5+ | Bold labels, high contrast for screen displays. |

## 🌟 Guidelines for Antigravity (Supervisor)

* **Node Detection**: Always check if `node` and `npx` are available before attempting CLI rendering.
* **Theme Injection**: Always inject `--theme default` or `--theme neutral` for scientific diagrams to avoid "noisy" default colors.
