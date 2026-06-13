# Evaluation Cases — make-a-diagram

TDD test cases for validating the skill's trigger rate and output quality.
Each case specifies the user prompt, expected diagram type, and a rubric.

## Case Format

```
input: "<user prompt>"
expects:
  type: <diagram type>
  contains: [<expected elements in output>]
  rubric:
    correct_type: <pass|fail>
    valid_syntax: <pass|fail>
    elk_default: <pass|fail>
    output_structure: <pass|fail>
```

## Test Cases

### E-01: Flowchart — Auth Flow
```
input: "Create a flowchart showing user authentication with login, MFA check, and session creation"
expects:
  type: flowchart
  contains: ["Login", "MFA", "Session"]
  rubric:
    correct_type: pass
    valid_syntax: pass
    elk_default: pass
    output_structure: pass
```

### E-02: Sequence Diagram — API Call
```
input: "Sequence diagram for a payment API where client calls gateway, gateway calls payment processor, and processor returns confirmation"
expects:
  type: sequenceDiagram
  contains: ["Client", "Gateway", "Processor", "confirmation"]
  rubric:
    correct_type: pass
    valid_syntax: pass
    elk_default: n/a (sequence diagram)
    output_structure: pass
```

### E-03: Class Diagram — Domain Model
```
input: "Class diagram showing User, Order, and Product with their attributes and relationships"
expects:
  type: classDiagram
  contains: ["User", "Order", "Product", "+", "-"]
  rubric:
    correct_type: pass
    valid_syntax: pass
    elk_default: n/a
    output_structure: pass
```

### E-04: ER Diagram — E-commerce
```
input: "ER diagram for an e-commerce system with customers, orders, products, and line items"
expects:
  type: erDiagram
  contains: ["CUSTOMER", "ORDER", "PRODUCT", "LINE_ITEM", "||--o{"]
  rubric:
    correct_type: pass
    valid_syntax: pass
    elk_default: pass
    output_structure: pass
```

### E-05: State Diagram — Order Lifecycle
```
input: "State diagram for an order lifecycle from pending through shipped to delivered or cancelled"
expects:
  type: stateDiagram-v2
  contains: ["Pending", "Processing", "Shipped", "Delivered", "Cancelled", "[*]"]
  rubric:
    correct_type: pass
    valid_syntax: pass
    elk_default: n/a
    output_structure: pass
```

### E-06: Block Diagram — Event-Driven Architecture
```
input: "Block diagram showing producers pushing to an event bus, with three consumers reading from it"
expects:
  type: block-beta
  contains: ["Producer", "Event Bus", "Consumer", "columns"]
  rubric:
    correct_type: pass
    valid_syntax: pass
    elk_default: n/a
    output_structure: pass
```

### E-07: GitGraph — Branch Strategy
```
input: "GitGraph showing main branch with develop and feature branches, plus a hotfix branch merged to both"
expects:
  type: gitGraph
  contains: ["commit", "branch", "merge", "checkout"]
  rubric:
    correct_type: pass
    valid_syntax: pass
    elk_default: n/a
    output_structure: pass
```

### E-08: Sankey — Energy Flow
```
input: "Sankey diagram showing energy flow from solar, wind, and coal sources to grid, storage, and consumption"
expects:
  type: sankey
  contains: ["Solar", "Wind", "Coal", "Grid", ","] # CSV-like format
  rubric:
    correct_type: pass
    valid_syntax: pass
    elk_default: n/a
    output_structure: pass
```

### E-09: C4 Context — System Architecture
```
input: "C4 System Context diagram for an Internet Banking System showing customer, banking staff, and external payment gateway"
expects:
  type: C4Context
  contains: ["Person", "System", "Rel"]
  rubric:
    correct_type: pass
    valid_syntax: pass
    elk_default: pass
    output_structure: pass
```

### E-10: Quadrant Chart — Prioritization Matrix
```
input: "Quadrant chart plotting feature requests by impact and effort, labeling each quadrant"
expects:
  type: quadrantChart
  contains: ["x-axis", "y-axis", "quadrant-1", "quadrant-2"]
  rubric:
    correct_type: pass
    valid_syntax: pass
    elk_default: n/a
    output_structure: pass
```

### E-11: ASCII Output
```
input: "Create a flowchart of a CI/CD pipeline and render it as ASCII art too"
expects:
  type: flowchart
  contains: ["Build", "Test", "Deploy"]
  ascii_rendered: true
  rubric:
    correct_type: pass
    valid_syntax: pass
    ascii_generated: pass
    output_structure: pass
```

### E-12: Output Directory Convention
```
input: "Diagram showing user registration flow"
expects:
  output_dir: "docs/diagrams/"
  files: ["*.mmd", "*.svg", "*.png", "*.txt", "*_log.json"]
  rubric:
    correct_type: pass
    valid_syntax: pass
    output_location: pass
    output_structure: pass
```
