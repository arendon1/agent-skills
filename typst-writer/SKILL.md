---
name: typst-writer
description: Write correct and idiomatic Typst code. Defaults to `versatile-apa` (Spanish). Covers scripting, layout, math, and data loading.
---

# Typst Writer

**Write idiomatic Typst code. Defaults to `versatile-apa` (Spanish) for academic papers.**

## 🚨 Critical Syntax Rules

| Feature | Syntax | Example |
| :--- | :--- | :--- |
| **Arrays** | `(item1, item2)` | `(1, 2)` (Parentheses) |
| **Dictionaries** | `(key: val)` | `(name: "Typst")` (Colon) |
| **Content Blocks** | `[markup]` | `[*Bold* text]` (Square Brackets) |
| **Code Mode** | `#expression` | `#let x = 1` (Hash prefix) |
| **No Tuples** | N/A | Typst ONLY has Arrays |

## 📚 References

| Reference | Purpose |
| :--- | :--- |
| `references/scripting.md` | Logic, Loops, Functions, State |
| `references/layout.md` | Page Setup, Grids, Alignment |
| `references/math.md` | Math Mode Syntax & Symbols |
| `references/data.md` | Loading CSV, JSON, XML |
| `references/plotting.md` | Drawing & Plotting (CeTZ) |
| `references/packages.md` | Popular packages & search tips |
| `references/bibliography.md` | Citations & BibTeX management |

## 📂 Examples

| File | Description |
| :--- | :--- |
| `examples/manual-layout.typ` | Manual page setup (margins, headers) |
| `examples/academic-paper.typ` | **Default APA 7 Template** (Spanish) |

## 🛠️ Common Patterns

**Defined Functions:**
```typst
#let note(body) = rect(fill: yellow, body)
```

**State Management:**
```typst
#let counter = state("cnt", 0)
#context counter.get()
```

**Loops:**
```typst
#for item in items [ - #item ]
```

## 🔍 Troubleshooting

*   **"expected content, found..."**: You are in code mode but need markup. Wrap in `[]`.
*   **"expected expression..."**: You are in markup but need code. Add `#`.
*   **Unknown font**: Typst will fallback. Check font name.
