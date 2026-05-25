# Referencia de Layout

Controla la estructura visual del documento.

## Configuración de Página

```typst
#set page(
  paper: "a4",
  margin: (x: 2cm, y: 2.5cm),
  numbering: "1",
  columns: 2,
  header: align(right)[Mi Encabezado],
  footer: align(center)[#context counter(page).display()],
)
```

## Alineación

* **Direcciones**: `left`, `right`, `center`, `top`, `bottom`, `horizon`
* **Combinaciones**: `right + bottom`, `center + horizon`

## Contenedores

### Box
Contenedor en línea.
```typst
#box(stroke: 1pt, inset: 5pt)[Box en línea]
```

### Block
Contenedor a nivel de bloque.
```typst
#block(
  fill: luma(240),
  inset: 10pt,
  radius: 4pt,
  width: 100%,
  [Contenido del bloque]
)
```

## Grids y Stacks

### Grid
Potente layout 2D.
```typst
#grid(
  columns: (1fr, 2fr),
  rows: (auto, 60pt),
  gutter: 1em,
  [Arriba Izquierda], [Arriba Derecha],
  [Abajo Izquierda], [Abajo Derecha]
)
```

### Stack
Layout 1D simple.
```typst
#stack(
  dir: ttb,
  spacing: 10pt,
  [Item 1],
  [Item 2]
)
```

## Columnas

```typst
#columns(2, gutter: 15pt)[
  Este contenido fluirá en dos columnas.
]