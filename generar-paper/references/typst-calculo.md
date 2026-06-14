# Referencia de Modo Matemático

Typst tiene un sistema poderoso de composición matemática.

## Básicos

* **Matemáticas en línea**: `$ x^2 $`
* **Matemáticas en bloque**: Agregar espacios o nuevas líneas
  ```typst
  $
    sum_(i=1)^n i = (n(n+1)) / 2
  $
  ```

## Sintaxis y Símbolos

| Característica | Sintaxis | Output/Notas |
| :--- | :--- | :--- |
| **Subíndice** | `x_1` | Subíndice `1` |
| **Superíndice** | `x^2` | Superíndice `2` |
| **Fracciones** | `1/2` | Fracción |
| **Paréntesis** | `(...)` | Paréntesis auto-escalables |
| **Raíces** | `sqrt(x)` | Raíz cuadrada |
| **Raíces (n)** | `root(3, x)` | Raíz cúbica |
| **Texto** | `"text"` | Texto dentro de matemáticas |

## Símbolos Comunes

* **Griegos**: `alpha`, `beta`, `gamma`, `Delta`, `pi`, `mu`, `sigma`
* **Relaciones**: `=`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `subset`
* **Flechas**: `->`, `<-`, `=>`, `<=>`
* **Conjuntos**: `RR`, `ZZ`, `NN`, `QQ`, `CC`
* **Operaciones**: `+`, `-`, `*`, `div`, `times`

## Estructuras Avanzadas

### Matrices y Vectores
```typst
$ mat(
  1, 2;
  3, 4
) $

$ vec(x, y, z) $
```

### Casos
```typst
$ f(x) = cases(
  1 "si" x > 0,
  0 "de lo contrario"
) $
```

### Alineación Multi-línea
```typst
$
  f(x) &= (x + 1)^2 \
       &= x^2 + 2x + 1
$
```