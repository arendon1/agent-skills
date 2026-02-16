# Scientific Visualization Best Practices

Adherence to these standards ensures your diagrams are "Publication-Ready".

## 1. Typography

* **Sans-Serif**: Always use Arial, Helvetica, or Inter.
* **Scale**: Maintain consistent font sizes across all labels.
* **Contrast**: Black text on white/light backgrounds only.

## 2. Mermaid Scientific Styling (Subgraphs & Themes)

When using Mermaid, apply these CSS/Theming overrides:

* **Theme**: Use `default` or `neutral`.
* **Colors**: Avoid bright neon colors. Use a muted palette (Academic Blue, Sage Green, Slate Gray).
* **Transparency**: Always export PNGs with `-b transparent` for flexible integration into papers.

## 3. Logical Flow

* **Hierarchy**: Left-to-Right (LR) for time progression; Top-to-Bottom (TD) for hierarchies.
* **Consistency**: Group related components into `subgraph` blocks with clear titles.

## 4. Accessibility

* **Okabe-Ito**: If using multiple colors, follow the Okabe-Ito palette for colorblind safety.
* **Contrast Ratio**: Ensure a minimum 4.5:1 ratio for all text elements.
