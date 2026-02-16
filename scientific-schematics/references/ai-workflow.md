# Scientific Interactive Workflow (v2.3)

This document defines the specialized refinement and rendering logic using @context-engineer methodology and the "Shadow Pipeline" for universal compatibility.

## 1. The Decision Matrix

Depending on the environment and complexity:

* **Complex Visuals** (e.g., biological signaling, 3D-like neural nets) → `generate_image`.
* **Structural Logic** (e.g., flowcharts, system blocks, sequences) → **Mermaid/SVG Fallback**.

## 2. The "Shadow Pipeline" (Automated Fallback Rendering)

To ensure the diagrams are usable even outside of the LLM context, we implement this automation:

1. **Generation**:

    ```mermaid
    [Agent Logic] --> (.mmd file)
    ```

2. **Detection**: Agent checks for `node -v` and `npx -v`.
3. **Rendering**:

    ```bash
    npx -p @mermaid-js/mermaid-cli mmdc -i input.mmd -o output.svg
    npx -p @mermaid-js/mermaid-cli mmdc -i input.mmd -o output.png -s 2 -b transparent
    ```

4. **Cleaning**: The logic ensures no temporary files clutter the root; everything is moved to `./figures/`.

## 3. Multi-Dimensional Rubric (Ref: context-engineer/evaluation.md)

Every audit produces a numeric score based on these weights:

* **Accuracy (30%)**: Correctness of the scientific model.
* **Clarity (25%)**: Professional spacing and background.
* **Labels (25%)**: Readability and size.
* **Logic (20%)**: Flow direction and grouping.

## 4. User Interaction & Hito de Decisión

* **The Checkpoint**: Execution stops after a proposal (Pixel or Vector) is ready.
* **The Question**: "Is this diagram accurate for your [Doc-Type]? Should I refine the logic or the rendering?"
* **Centralized Storage**: All files are stored in `/figures/` for easy access.
