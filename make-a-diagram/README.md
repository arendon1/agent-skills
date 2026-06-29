# make-a-diagram

**Generate software diagrams by describing them in natural language.**

Renders Mermaid diagrams to SVG, PNG, and ASCII art using beautiful-mermaid
and mermaid-cli, with ELK layout engine by default.

## Usage

Ask: *"Create a [diagram type] showing [description]"*

Examples:
- "Sequence diagram for auth microservice calling user service"
- "Flowchart of order processing pipeline with error handling"
- "C4 System Context diagram for an e-commerce platform"
- "Sankey diagram showing user flow through the conversion funnel"
- "Quadrant chart for feature prioritization by effort and impact"
- "Block diagram of event-driven architecture with Kafka"
- "Class diagram for domain model with User, Order, Product"
- "ER diagram for social media schema with posts, comments, likes"

## Workflow

1. **Describe** what you want diagrammed
2. **Review** the Mermaid code and rendered outputs
3. **Refine** via feedback until approved

## Supported Diagram Types

Flowchart, Sequence, Class, ER, State, Block, C4 (Context & Container),
Sankey, Quadrant Chart, Packet, Gantt, Timeline, GitGraph, Mindmap,
XY Chart, Pie, Journey, Requirement

## Output

Diagrams render to `docs/diagrams/` in your project workspace:
- `[name].mmd` — Source (editable)
- `[name].svg` — Vector (beautiful-mermaid)
- `[name].png` — Raster (mermaid-cli)
- `[name].txt` — ASCII art (beautiful-mermaid, terminal-friendly)
- `[name]_log.json` — Audit metadata

## Dependencies

Run `bash scripts/check-deps.sh` to verify your environment.
Requires Node.js, @mermaid-js/mermaid-cli, and beautiful-mermaid.
