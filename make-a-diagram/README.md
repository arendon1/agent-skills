# make-a-diagram

**Generate software diagrams by describing them in natural language.**

## Usage

Ask: *"Create a [diagram type] showing [description]"*

Examples:
- "Sequence diagram for auth microservice calling user service"
- "Flowchart of order processing pipeline"
- "Block diagram of event-driven architecture"
- "Class diagram for domain model"

## Workflow

1. **Describe** what you want diagrammed
2. **Review** the Mermaid code and rendered output
3. **Refine** via feedback until approved

## Supported Types

Flowchart, Sequence, Class, ER, State, Block, Gantt, Mindmap

## Output

Diagrams render to `figures/[name].svg` and `.png` automatically.