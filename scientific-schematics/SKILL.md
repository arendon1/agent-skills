---
name: scientific-schematics
description: >-
  Advanced scientific diagram generator with AI-native iterative refinement.
  Use when creating Mermaid diagrams, scientific schematics, or technical visualizations.
license: Apache-2.0
metadata:
  version: "2.3.0"
  language: en
  author: Antigravity
---

# Scientific Schematics (Mermaid-Native)

**Precision scientific visualization focusing on structural accuracy and universal accessibility.**

## 🧠 Brain-Power: Structural Visualization

This skill prioritizes **Structural Code** (Mermaid) over raster images to ensure transparency, reproducibility, and high fidelity in technical environments.

1. **Logic-First**: We use the appropriate Mermaid diagram for the scientific concept.
2. **Hybrid Fallback**: `generate_image` is reserved for complex organic textures or artistic renderings that lack a structural schema.

## 🔄 The Master Workflow (Interactive)

### Case A: Structural Blueprint (Primary)

When the concept can be modeled as a flow, hierarchy, or interaction:

1. **Selection**: Choose the optimal Mermaid type (see 📊 Mermaid Capability Map).
2. **Generation**: I generate valid Mermaid.js code with scientific themes.
3. **Shadow Pipeline (Zero-Configuration Rendering)**:
    * Code saved to `figures/[name].mmd`.
    * **Auto-Render**: I run `npx @mermaid-js/mermaid-cli` to generate **SVG** (Journal) and **PNG** (Presentation).
4. **Validation**: I verify syntax and visual hierarchy.

### Case B: High-Fidelity Artistic Proposals (Secondary)

When Mermaid cannot represent the complexity (e.g., a realistic anatomical heart):

1. **Prompt Sharpening**: Structured manifests for `generate_image`.
2. **Generation**: Create an image and store it in `figures/[name].png`.
3. **Audit**: Evaluation against Accuracy and Clarity.

## 📊 Mermaid Capability Map (Scientific Context)

| Diagram Type | Best for... | Example |
| :--- | :--- | :--- |
| **Flowchart (graph TD)** | Decision trees, mechanisms, experimental protocols. | Enzyme-substrate interactions. |
| **Sequence Diagram** | Cascades, signal transduction, multi-step protocols. | Phototransduction pathway. |
| **Class Diagram** | Ontologies, taxonomies, data structures. | Phylogenetic trees or software architecture. |
| **ER Diagram** | Relational data, chemical bonds, networks. | Metabolic network relationships. |
| **State Diagram** | Cycle transitions, phase changes. | Cellular cycle or phase transitions. |
| **Gantt / Timeline** | Study durations, historical milestones. | Clinical trial stages. |
| **Mindmap** | Brainstorming, conceptual mapping. | Research field breakdown. |
| **XY / Sankey** | Trends, resource/energy flux. | Energy distribution in ecosystems. |
| **Block Diagram** | Modular architectures, lab setups. | Signal processing blocks. |

## 🏢 Workspace Organization

Outputs should be placed in the project's target directory (e.g., `docs/assets/` or `assets/diagrams/`) to maintain context.

```text
[project-root]/
├── [target-dir]/            # Specified by task context
│   ├── [name].mmd          # Source Mermaid code (Editable)
│   ├── [name].svg          # Vector output (Publish Ready)
│   ├── [name].png          # Raster output (Static)
│   └── [name]_log.json     # Review & Metadata log
```

## 📊 Document Quality Standards

| Type | Target | Logic |
| :--- | :--- | :--- |
| **Journal** | 9.0+ | SVG required. Zero ambiguity. Structural accuracy over aesthetics. |
| **Technical** | 8.0+ | High contrast, clear labels, academic palette (`--theme neutral`). |

## 🌟 Guidelines for Antigravity

* **Output Flex**: Prefer absolute paths or paths relative to the project root for outputs.
* **Theme Enforcement**: Use `--theme neutral` as the default for scientific clarity.
* **Node Detection**: Check for `node` and `npx` before rendering. If missing, provide the .mmd code for the user's VS Code preview.
