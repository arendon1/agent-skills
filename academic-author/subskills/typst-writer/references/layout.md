# Layout Reference

Control the visual structure of your document.

## Page Setup
Use the `#set page(..)` rule to configure global page settings.

```typst
#set page(
  paper: "a4", // "us-letter", "a5", etc.
  margin: (x: 2cm, y: 2.5cm), // Dictionary for margins
  numbering: "1", // Page numbering style
  columns: 2, // Multi-column layout
  flipped: false, // Landscape if true
  header: align(right)[My Header],
  footer: align(center)[#context counter(page).display()],
)
```

## Alignment
Use `#align(alignment, content)` or set alignment for a scope.
*   **Directions**: `left`, `right`, `center`, `top`, `bottom`, `horizon` (vertical center).
*   **Combinations**: `right + bottom`, `center + horizon`.

```typst
#align(center + horizon)[
  This text is perfectly centered on the page.
]
```

## Containers

### Box
Inline container that flows with text.
```typst
#box(stroke: 1pt, inset: 5pt)[Inline Box]
```

### Block
Block-level container that takes full width (unless sized).
```typst
#block(
  fill: luma(240),
  inset: 10pt,
  radius: 4pt,
  width: 100%,
  [Block content]
)
```

## Grids & Stacks

### Grid
Powerful 2D layout.
```typst
#grid(
  columns: (1fr, 2fr), // Fr = fraction of available space
  rows: (auto, 60pt),
  gutter: 1em, // Spacing between cells
  [Top Left], [Top Right],
  [Bottom Left], [Bottom Right]
)
```

### Stack
Simple 1D layout (vertical or horizontal).
```typst
#stack(
  dir: ttb, // top-to-bottom
  spacing: 10pt,
  [Item 1],
  [Item 2]
)
```

## Columns
Create local multi-column regions (distinct from page-level columns).
```typst
#columns(2, gutter: 15pt)[
  This content will flow into two columns.
  When the first column is full, it moves to the second.
]
```
