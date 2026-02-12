# Graphics & Plotting Reference

Integrate drawings and charts using the `cetz` package (CeTZ: Creative Typst Zee).

## Setup
Import the core package and the plot module (if needed).

```typst
#import "@preview/cetz:0.3.1"
#import "@preview/cetz-plot:0.1.0"
```

*GitHub Repository: [cetz-package/cetz](https://github.com/cetz-package/cetz)*

## Basic Drawing (Canvas)

Use the `canvas` function to define a drawing area. Coordinates are `(x, y)`.

```typst
#cetz.canvas({
  import cetz.draw: *

  // Basic shapes
  rect((-1, -1), (1, 1), fill: blue.lighten(80%))
  circle((0, 0), radius: 0.5, fill: yellow)
  line((-2, 0), (2, 0), mark: (end: ">"))

  // Styling
  content((0, -2), [Fig A. Geometry], text: 10pt)
})
```

## Plotting (Charts)

Use the `plot` module for data visualization.

```typst
#cetz.canvas({
  import cetz.plot
  
  plot.plot(
    size: (10, 6),
    x-tick-step: 1,
    y-tick-step: 2,
    {
      // Line plot
      plot.add(
        domain: (0, 10), 
        x => calc.sin(x) * 4, 
        label: $f(x) = 4 sin(x)$
      )
      
      // Scatter points
      plot.add(
        ((1, 1), (3, 3), (5, 2), (8, 6)), 
        mark: "o", 
        style: (stroke: none, fill: red)
      )
    }
  )
})
```

## Common Drawing Elements

| Function | Params | Description |
| :--- | :--- | :--- |
| `line(start, end)` | `start`, `end`: Coordinates | Draws a line segment or path |
| `rect(a, b)` | `a`, `b`: Corner coords | Draws a rectangle |
| `circle(pos)` | `radius` | Draws a circle |
| `arc(start, stop, ...)` | `mode: "PIE"` | Draws arcs or pie slices |
| `bezier(start, end, ...)` | `control` | Draws bezier curves |

## Tips
- Use `name` parameter to label nodes for connecting lines later.
- Use `anchor` to position content relative to points.
- Combine with Typst loops for procedural generation.
