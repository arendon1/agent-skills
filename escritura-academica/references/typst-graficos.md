# Gráficos y Plotting

Integrar dibujos y gráficos usando el paquete `cetz`.

## Configuración

```typst
#import "@preview/cetz:0.3.1"
#import "@preview/cetz-plot:0.1.0"
```

## Dibujo Básico (Canvas)

```typst
#cetz.canvas({
  import cetz.draw: *

  rect((-1, -1), (1, 1), fill: blue.lighten(80%))
  circle((0, 0), radius: 0.5, fill: yellow)
  line((-2, 0), (2, 0), mark: (end: ">"))
})
```

## Gráficos (Charts)

```typst
#cetz.canvas({
  import cetz.plot

  plot.plot(
    size: (10, 6),
    x-tick-step: 1,
    y-tick-step: 2,
    {
      plot.add(
        domain: (0, 10),
        x => calc.sin(x) * 4,
        label: $f(x) = 4 sin(x)$
      )
    }
  )
})
```

## Elementos Comunes

| Función | Descripción |
| :--- | :--- |
| `line(start, end)` | Línea o ruta |
| `rect(a, b)` | Rectángulo |
| `circle(pos)` | Círculo |
| `arc(start, stop, ...)` | Arco |
| `bezier(start, end, ...)` | Curva de Bézier |