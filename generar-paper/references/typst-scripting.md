# Referencia de Scripting Typst

## Distinciones Críticas de Sintaxis

### Estructuras de Datos

- **Arrays**: Usar `()` paréntesis
  ```typst
  #let colors = (red, blue, green)
  ```

- **Diccionarios**: Usar `()` con pares clave-valor
  ```typst
  #let config = (name: "value", count: 5)
  ```

- **Bloques de contenido**: Usar `[]` corchetes
  ```typst
  #let heading = [== Mi Título]
  ```

**IMPORTANTE**: Typst NO tiene tuplas. Solo arrays.

### Definición de Funciones

```typst
#let greet(name) = [Hola, #name!]
#let box-style(fill: none, stroke: 1pt) = { ... }
```

### Condicionales y Loops

```typst
#if condition {
  [rama verdadera]
} else {
  [rama falsa]
}

#for item in array {
  [Procesando #item]
}
```

### Interpolación de Strings

```typst
#let name = "Mundo"
[Hola #name]
```

## Patrones Comunes

### Funciones de Estilo Personalizado

```typst
#let highlight(color, body) = {
  box(fill: color.lighten(80%), inset: 3pt, body)
}
```

### Gestión de Estado

```typst
#let counter = state("my-counter", 0)
#counter.update(x => x + 1)
#context counter.get()
```

### Ayudantes de Layout

```typst
#stack(
  spacing: 1em,
  [Primer item],
  [Segundo item]
)

#grid(
  columns: (1fr, 2fr),
  rows: auto,
  gutter: 10pt,
  [Celda 1], [Celda 2]
)
```

## Errores Comunes

1. **Acceso a arrays**: Usar `.at()`, no `[]`
2. **Bloques de contexto**: Requeridos para acceder a estado
3. **Asignación**: Usar `let`, no `=` solo

## Verificación del Entorno

Antes de compilar un documento Typst, verificar que `typst` esté instalado:

```bash
typst --version
```

Si no está disponible, informar al usuario y ofrecer alternativas.