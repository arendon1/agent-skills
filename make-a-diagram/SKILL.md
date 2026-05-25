---
name: make-a-diagram
description: >-
  Generate software architecture diagrams, flowcharts, sequence diagrams, and
  technical schematics using Mermaid. Use when users ask to diagram, visualize,
  or map software concepts.
license: Apache-2.0
language: en
metadata:
  version: "1.1.0"
  author: Antigravity
---

# make-a-diagram

**Software diagram generator using Mermaid (v11+) for structured, reproducible technical visualizations.**

## Principles

1. **Mermaid-First**: All diagrams use Mermaid.js (v11) code. Clean, text-based, version-control-friendly.
2. **Zero-Config Rendering**: Save `.mmd` + run `mermaid-cli` -> SVG + PNG auto-generated.
3. **Software Scope**: Flowcharts, sequence diagrams, class diagrams, ER diagrams, state machines, architecture block diagrams, GitGraph, timelines. Not for UI mockups or organic visuals.

## Workflow

### Generation

1. **Select Mermaid Type** based on the concept (see Capability Map below).
2. **Write Mermaid code** with software-appropriate themes (`neutral` default).
3. **Auto-Render**: Save to `figures/[name].mmd`, run `npx @mermaid-js/mermaid-cli` to produce SVG + PNG.
4. **Validate**: Check syntax, label clarity, logical geometry.

### Refinement Loop

1. Show user the rendered diagram.
2. Accept feedback (labels, colors, layout, detail level).
3. Iterate until approved.

## Mermaid Capability Map (v11)

| Diagram Type | Best for | Example |
| :--- | :--- | :--- |
| **Flowchart** (`graph TD/LR`) | Decision trees, data flow, pipelines, protocols | Auth flow, request lifecycle, CI/CD pipeline |
| **Sequence Diagram** | API calls, service interactions, message passing | microservice choreography, auth flow |
| **Class Diagram** | Object-oriented structure, taxonomies | Domain model, API schema, data model |
| **ER Diagram** | Database schemas, relationships | User-Order-Product relations |
| **State Diagram** | State machines, lifecycle transitions | Order status, session states, API lifecycle |
| **Block Diagram** | System architecture, component layout | Event-driven architecture, microservices |
| **Gantt** | Release phases, sprint milestones | Deployment schedule, project timeline |
| **Timeline** | Sequential events, history | API versioning, incident timeline |
| **GitGraph** | Git repository history | Branch strategy, release flow |
| **Mindmap** | Feature brainstorming, concept mapping | Domain bounded contexts |
| **Architecture** | High-level system design | Cloud architecture, infrastructure |
| **Requirement** | Requirements traceability | Feature requirements mapping |

## Flowchart Node Shapes (v11.3+)

Mermaid v11.3 introduced 30+ new shapes. Use the shape that matches the semantic meaning:

| Shape | Keyword | Use case |
| :--- | :--- | :--- |
| Rectangle | `rect` or default | Process, service |
| Diamond | `diam` | Decision |
| Hexagon | `hex` | Preparation, condition |
| Stadium | `stadium` | Terminal, start/end |
| Cylinder | `cyl` or `db` | Database |
| Document | `doc` | File, report |
| Circle | `circle` | Start/end |
| Cloud | `cloud` | External service |
| Folder | `folder` | Namespace, module |
| Queue | `queue` | Message queue |
| Parallelogram | `parallelogram` | Input/output |

New syntax: `A@{ shape: rect }` or `A["Label"]:::className`.

## Sequence Diagram Features (v11+)

- **Participants**: implicit or explicit declaration with `participant`
- **Actor types**: `participant`, `actor`, `entity`, `control`, `database`, `queue`, `collections`
- **Aliases**: `participant A as AliasName` or inline config `{ alias: "Name" }`
- **Boxes/Groups**: `box Color GroupName ... end box`
- **Half-arrows** (v11.12.3): `-|\`, `-|/`, `\-`, `/-`, `\\-`, `-//`, `//-`
- **Central connections**: `A --()--> B` for central lifeline
- **Auto-numbering**: `autonumber <start> <increment>` (v11.15.0+)
- **Actor menus**: `link Actor: Label @ URL`
- **Create/Destroy**: `create participant B` before message

### Sequence Diagram Arrow Types

```
->  Solid without arrow       -->  Dotted without arrow
->> Solid with arrow         -->> Dotted with arrow
-x   Solid with cross        --x  Dotted with cross
-)   Solid with open arrow   --)  Dotted with open arrow
<<->>  Solid bidirectional   <<-->>  Dotted bidirectional
```

## Class Diagram Features (v11+)

- **Members**: `+public -private #protected ~package` visibility
- **Relationships**: `<|--` inheritance, `*--` composition, `o--` aggregation, `-->` association, `..>` dependency, `..|>` realization
- **Generics**: `List~int~`, `Map~String, User~`
- **Annotations**: `<<Interface>>`, `<<Abstract>>`, `<<Service>>`, `<<Enumeration>>`
- **Cardinality**: `"1"`, `"0..1"`, `"1.."`, `"*"`, `"n..m"`
- **Namespaces**: `namespace ns { ... }` with nested support (v11.15.0+)
- **Lollipop interfaces**: `foo --() bar`
- **Return types**: `+getName() String`
- **Classifiers**: `$` static, `*` abstract

## Block Diagram Features (v11+)

- **Column layout**: author controls positioning
- **Composite blocks**: `block D ... D --- end block`
- **Width spanning**: `a --2--- b` (block a spans 2 columns)
- **Shapes**: round, stadium, subroutine, cylinder, circle, rhombus, hexagon, trapezoid, etc.
- **Edges with labels**: `A --> B : label text`
- **Class styling**: `classDef className fill:#f9f,stroke:#333`

## State Diagram Features (v11+)

- **Simple states**: `State` or `state "Description"`
- **Composite states**: `state Parent { child1 child2 }`
- **Transitions**: `State1 --> State2 : transition label`
- **Start/End**: `[*] --> Start`, `End --> [*]`
- **Choice**: `<<choice>>` decision point
- **Fork/Join**: `<<fork>>`, `<<join>>`
- **Concurrency**: `--` separator for parallel states
- **Notes**: `note right of State : comment`

## Theming

Default theme: `neutral` (print-friendly, monochrome-safe).

Available themes: `default`, `neutral`, `dark`, `forest`, `base` (customizable).

Override via frontmatter:
```
---
config:
  theme: dark
---
```

Customize via `themeVariables` using `base` theme.

## Rendering

### Requirements
- Node.js + npm
- `npx @mermaid-js/mermaid-cli`

### Commands
```bash
npx @mermaid-js/mermaid-cli mmd -i figures/[name].mmd -o figures/[name].svg
npx @mermaid-js/mermaid-cli mmd -i figures/[name].mmd -o figures/[name].png -b png
```

### Fallback
If `node`/`npx` unavailable, provide `.mmd` code and direct user to [mermaid.live](https://mermaid.live/edit) for preview.

## Output Structure

```
[project-root]/
├── figures/
│   ├── [name].mmd      # Source (editable)
│   ├── [name].svg      # Vector (publish-ready)
│   ├── [name].png      # Raster (static)
│   └── [name]_log.json # Metadata + audit
```

## Quality Standards

| Target | Criteria |
| :--- | :--- |
| Architecture Doc | High contrast, clear component boundaries, minimal noise |
| Technical Spec | Accurate labels, logical layout, academic palette |
| README / Docs | Readable at small sizes, monochrome-safe |
| Presentation | 7.5+ | High contrast, simplified labels |