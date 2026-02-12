# AI Generation Workflow

## Smart Iterative Refinement

The AI generation system uses **smart iteration** - it only regenerates if quality is below the threshold for your document type (Journal, Conference, Poster, etc.).

### Workflow Steps
1.  **Generate**: Nano Banana Pro creates initial image.
2.  **Review**: Gemini 3 Pro evaluates quality (Accuracy, Clarity, Labels, Layout).
3.  **Decision**:
    *   **Score >= Threshold**: STOP (Success).
    *   **Score < Threshold**: Improve prompt based on critique -> Regenerate.
4.  **Repeat**: Until threshold met or max iterations reached.

### Quality Thresholds
| Document Type | Threshold |
| :--- | :--- |
| **Journal** | 8.5/10 |
| **Conference** | 8.0/10 |
| **Poster** | 7.0/10 |
| **Presentation** | 6.5/10 |

### Review Log
All iterations are saved with a JSON review log (`output_name.json`) containing scores, critiques, and early-stop reasoning.
