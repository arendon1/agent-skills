---
name: make-a-diagram
language: en
description: >-
  Generate software architecture diagrams, flowcharts, sequence diagrams,
  block diagrams, C4 models, ER schemas, Sankey flows, state machines,
  GitGraphs, timelines, and more using Mermaid (v11+) with ELK layout
  engine. Renders SVG, PNG, and ASCII art via beautiful-mermaid.
  Use when users ask to diagram, visualize, or map software concepts,
  system architecture, data flows, processes, or database schemas.
license: Apache-2.0
metadata:
  version: "2.0.0"
  author: Pi + Andrés (based on Antigravity v1.1.0)
---

# make-a-diagram

**Software diagram generator using Mermaid (v11+) with ELK layout, multi-format
rendering (SVG + PNG + ASCII), and automatic output to `docs/diagrams/`.**

## Principles

1. **Mermaid-First**: All diagrams use Mermaid.js (v11) — clean, text-based,
   version-control-friendly code.
2. **ELK Layout Default**: Every diagram uses the ELK layout engine for
   superior node placement on complex graphs.
3. **Multi-Format Output**: Every diagram produces SVG (vector), PNG (raster),
   and TXT (ASCII art) via beautiful-mermaid.
4. **Workspace Convention**: Output always lands in `<workspace_root>/docs/diagrams/`.
5. **Software Scope**: Architecture, data flow, processes, schemas, state
   machines, timelines. Not for UI mockups or organic visuals.

## Preflight

Before rendering, run the dependency check:

```bash
bash scripts/check-deps.sh
```

Required dependencies:
| Dependency | Purpose | Install |
| :--- | :--- | :--- |
| Node.js >= 18 | Runtime | https://nodejs.org |
| @mermaid-js/mermaid-cli | PNG rasterization | `npx @mermaid-js/mermaid-cli` (auto-download) |
| beautiful-mermaid | SVG + ASCII rendering | `npm install beautiful-mermaid` |

If the check fails, it prints installation hints. The render script also
runs this check automatically.

## Workflow

### Generation

1. **Select Mermaid Type** from the Capability Map below.
2. **Write Mermaid code** — include the ELK layout config in frontmatter.
3. **Save** to `docs/diagrams/[name].mmd`.
4. **Render** via `python scripts/render.py docs/diagrams/[name].mmd`
   (produces `.svg`, `.png`, `.txt`, `_log.json`).
5. **Validate**: check syntax, label clarity, logical geometry.

### Refinement Loop

1. Show user the rendered diagram (SVG for web/docs, PNG for slides, ASCII for CLI).
2. Accept feedback (labels, colors, layout, detail level).
3. Iterate until approved.

## Default Configuration (ELK Layout)

Every Mermaid diagram MUST include this frontmatter block:

```yaml
---
config:
  layout: elk
---
```

For flowchart-specific ELK renderer (alternative syntax):

```yaml
---
config:
  flowchart:
    defaultRenderer: elk
---
```

Exceptions: Sequence diagrams and GitGraphs do not use layout engines;
omit the `layout: elk` config for those types.

## Mermaid Capability Map (v11+)

| Diagram Type | Directive | Best for |
| :--- | :--- | :--- |
| **Flowchart** | `flowchart TD/LR` | Decision trees, data flow, pipelines, protocols |
| **Sequence** | `sequenceDiagram` | API calls, service interactions, message passing |
| **Class** | `classDiagram` | OOP structure, domain models, API schemas |
| **ER Diagram** | `erDiagram` | Database schemas, entity relationships |
| **State** | `stateDiagram-v2` | State machines, lifecycle transitions |
| **Block** | `block-beta` | System architecture, component layout |
| **C4 Context** | `C4Context` | High-level system context with actors |
| **C4 Container** | `C4Container` | Container-level architecture view |
| **Sankey** | `sankey` | Flow quantities between nodes |
| **Quadrant Chart** | `quadrantChart` | Prioritization matrices, 2D positioning |
| **Packet** | `packet` | Network packet structure, bit ranges |
| **Gantt** | `gantt` | Release phases, sprint milestones |
| **Timeline** | `timeline` | Sequential events, version history |
| **GitGraph** | `gitGraph` | Repository history, branch strategy |
| **Mindmap** | `mindmap` | Feature brainstorming, concept mapping |
| **XY Chart** | `xychart-beta` | Bar/line charts from data |
| **Pie** | `pie` | Proportions, distribution |
| **Journey** | `journey` | User journey, experience mapping |
| **Requirement** | `requirementDiagram` | Requirements traceability |

See `references/prompt-guide.md` for worked patterns for each type.

## Flowchart Node Shapes (v11.3+)

Mermaid v11.3 introduced 30+ expanded shapes via `@{ shape: name }` syntax.
See `references/shape-reference.md` for the complete catalog.

Quick reference — semantic mapping:

| Shape | Use case |
| :--- | :--- |
| `rect` (default) | Process, service |
| `diam` | Decision |
| `hex` | Preparation, condition |
| `stadium` | Start/end terminal |
| `cyl` | Database |
| `doc` | File, report |
| `circle` | Simple endpoint |
| `cloud` | External service |
| `folder` | Module, namespace |
| `queue` | Message queue |
| `parallelogram` | I/O, data entry |
| `trap-t` | Manual operation |
| `subroutine` | Predefined process |
| `hourglass` | Timed/wait state |
| `delay` | Timeout |
| `flag` | Milestone |
| `fork` | Concurrency start |

## Sequence Diagram Features (v11+)

- **Participants**: `participant`, `actor`, `entity`, `control`, `database`,
  `queue`, `collections`
- **Aliases**: `participant A as AliasName`
- **Boxes**: `box Color GroupName ... end box`
- **Autonumbering**: `autonumber <start> <increment>`
- **Create/Destroy**: `create participant B`, `destroy participant B`
- **Central connections**: `A --()--> B` for central lifeline
- **Actor menus/links**: `link Actor: Label @ URL`
- **Half-arrows** (v11.12.3+): `-|\`, `-|/`, `\-`, `/-`, `\\-`, `-//`, `//-`

Arrow types: `->` solid, `-->` dotted, `->>` solid with arrow, `-->>` dotted
with arrow, `-x` solid with cross, `--x` dotted with cross, `-)` solid open,
`--)` dotted open, `<<->>` solid bidirectional, `<<-->>` dotted bidirectional.

## Class Diagram Features (v11+)

- **Visibility**: `+public -private #protected ~package`
- **Relationships**: `<|--` inheritance, `*--` composition, `o--` aggregation,
  `-->` association, `..>` dependency, `..|>` realization
- **Generics**: `List~int~`, `Map~String, User~`
- **Annotations**: `<<Interface>>`, `<<Abstract>>`, `<<Service>>`, `<<Enumeration>>`
- **Cardinality**: `"1"`, `"0..1"`, `"1.."`, `"*"`, `"n..m"`
- **Namespaces** (v11.15.0+): `namespace ns { ... }`
- **Lollipop interfaces**: `foo --() bar`

## Block Diagram Features (v11+)

- **Column layout** with `columns N`
- **Composite blocks**: `block D ... end block`
- **Width spanning**: `a --2--- b`
- **Shapes**: `round`, `stadium`, `subroutine`, `cylinder`, `circle`, `rhombus`,
  `hexagon`, `trapezoid`
- **Edges with labels**: `A --> B : label text`
- **Class styling**: `classDef className fill:#f9f,stroke:#333`

## State Diagram Features (v11+)

- **Composite states**: `state Parent { child1 child2 }`
- **Choice nodes**: `<<choice>>`
- **Fork/Join**: `<<fork>>`, `<<join>>`
- **Concurrency**: `--` separator for parallel states
- **Notes**: `note right of State : comment`

## Theming

Default theme: `neutral` (print-friendly, monochrome-safe).

Available themes: `default`, `neutral`, `dark`, `forest`, `base` (customizable).

Override via frontmatter:

```yaml
---
config:
  theme: dark
  layout: elk
---
```

Customize via `themeVariables` with `base` theme for full color control.

## Rendering Pipeline

### Scripts

| Script | Purpose |
| :--- | :--- |
| `check-deps.sh` | Preflight dependency checker |
| `render.py` | Orchestration: SVG + PNG + ASCII + log |
| `render_beautiful.mjs` | beautiful-mermaid wrapper (called by render.py) |

### Commands

```bash
# Run preflight check
bash scripts/check-deps.sh

# Render all formats (SVG + PNG + ASCII + log)
python scripts/render.py docs/diagrams/[name].mmd

# Render to custom output directory
python scripts/render.py docs/diagrams/[name].mmd -o ./out

# ASCII-only with custom spacing
node scripts/render_beautiful.mjs ascii input.mmd output.txt --padding-x 7 --padding-y 3

# ASCII in pure-ASCII mode (no Unicode box-drawing)
node scripts/render_beautiful.mjs ascii input.mmd output.txt --ascii-only
```

### Manual (if scripts unavailable)

```bash
# SVG + PNG via mermaid-cli
npx @mermaid-js/mermaid-cli mmd -i docs/diagrams/[name].mmd -o docs/diagrams/[name].svg
npx @mermaid-js/mermaid-cli mmd -i docs/diagrams/[name].mmd -o docs/diagrams/[name].png -b png
```

### Fallback

If no renderers are available, provide `.mmd` code and direct user to
[mermaid.live](https://mermaid.live/edit) for preview.

## Output Structure

```
<workspace_root>/
└── docs/
    └── diagrams/
        ├── [name].mmd        # Source (editable)
        ├── [name].svg        # Vector (web/docs — beautiful-mermaid)
        ├── [name].png        # Raster (slides — mermaid-cli)
        ├── [name].txt        # ASCII art (CLI/terminal — beautiful-mermaid)
        └── [name]_log.json   # Metadata + audit log
```

## Quality Standards

| Target | Criteria |
| :--- | :--- |
| Architecture Doc | High contrast, clear component boundaries, minimal noise |
| Technical Spec | Accurate labels, logical layout, academic palette |
| README / Docs | Readable at small sizes, monochrome-safe |
| Presentation | High contrast, simplified labels, 6-8 elements max |
| CLI / Terminal | Pure ASCII option available, max 80 chars wide |
