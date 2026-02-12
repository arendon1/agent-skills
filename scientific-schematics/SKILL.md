---
name: scientific-schematics
description: "Create publication-quality scientific diagrams using Nano Banana Pro AI with smart iterative refinement. Uses Gemini 3 Pro for quality review. Only regenerates if quality is below threshold for your document type. Specialized in neural network architectures, system diagrams, flowcharts, biological pathways, and complex scientific visualizations."
allowed-tools: [Read, Write, Edit, Bash]
---

# Scientific Schematics

**Generate publication-ready diagrams with AI-powered iterative refinement.**

## 🚀 Quick Start

**1. Set API Key:**
```bash
export OPENROUTER_API_KEY='your_api_key_here'
```

**2. Generate Diagram:**
```bash
python scripts/generate_schematic.py "Your detailed diagram description" -o output.png
```

**3. Specify Document Type (Adjusts Quality Threshold):**
```bash
python scripts/generate_schematic.py "desc" -o out.png --doc-type journal      # Highest (8.5/10)
python scripts/generate_schematic.py "desc" -o out.png --doc-type conference   # High (8.0/10)
python scripts/generate_schematic.py "desc" -o out.png --doc-type poster       # Medium (7.0/10)
python scripts/generate_schematic.py "desc" -o out.png --doc-type presentation # Fast (6.5/10)
```

## 📚 References

| Reference | Contents |
| :--- | :--- |
| `references/ai-workflow.md` | Smart iteration & quality thresholds logic |
| `references/prompt-guide.md` | How to write effective diagram prompts |
| `references/troubleshooting.md` | Solving common generation issues |
| `references/best_practices.md` | Design & accessibility standards |
| `references/diagram_types.md` | Catalog of diagram types (if available) |

## 🌟 Capabilities

*   **Neural Networks**: Transformers, CNNs, RNNs.
*   **Flowcharts**: CONSORT, PRISMA, Algorithms.
*   **Pathways**: Biological signaling, metabolic.
*   **Architectures**: System block diagrams, IoT, Cloud.
*   **Circuits**: Electrical schematics.

## 🛠️ Advanced Usage

**Custom Iterations:**
```bash
# Force up to 2 refinement rounds
python scripts/generate_schematic.py "desc" --iterations 2
```

**Python API:**
```python
from scripts.generate_schematic_ai import ScientificSchematicGenerator
gen = ScientificSchematicGenerator(api_key="...")
gen.generate_iterative("prompt", "out.png", iterations=2)
```
