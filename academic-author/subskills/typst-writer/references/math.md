# Math Mode Reference

Typst has a powerful math typesetting system. To enter math mode, wrap equations in `$` signs.

## Basics

*   **Inline Math**: `$ x^2 $` (No spaces inside `$` for inline in older versions, but current best practice is spaces for readability: `$ x^2 $` renders inline).
*   **Block Math**: Add spaces or newlines to force display mode.
    ```typst
    $ x^2 $  // Inline
    $ x^2 $  // Block (if strictly following display rules, typically depends on context or explicit block style)
    ```
    *Better practice:* Use spaces for readability. Block capability often inferred or explicit.

    ```typst
    $
      sum_(i=1)^n i = (n(n+1)) / 2
    $
    ```
    (Multiline block)

## Syntax & Symbols

| Feature | Syntax | Output/Notes |
| :--- | :--- | :--- |
| **Subscript** | `x_1` | Subscript `1` |
| **Superscript** | `x^2` | Superscript `2` |
| **Fractions** | `1/2` | Displayed fraction |
| **Parens** | `(...)` | Auto-scaling parentheses |
| **Roots** | `sqrt(x)` | Square root |
| **Roots (n)** | `root(3, x)` | Cube root |
| **Text** | `"text"` | Text inside math |

## Common Symbols

*   **Greek**: `alpha`, `beta`, `gamma`, `Delta`, `pi`, `mu`, `sigma`
*   **Relations**: `=`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `subset`
*   **Arrows**: `->`, `<-`, `=>`, `<=>`, `-->`
*   **Sets**: `RR` (Real), `ZZ` (Integer), `NN` (Natural), `QQ` (Rational), `CC` (Complex)
*   **Operations**: `+`, `-`, `*` (dot), `times` (x), `div`

## Advanced Structures

### Matrices & Vectors
```typst
$ mat(
  1, 2;
  3, 4
) $

$ vec(x, y, z) $
```

### Cases
```typst
$ f(x) = cases(
  1 "if" x > 0,
  0 "otherwise"
) $
```

### Multi-line Alignment
Use `&` for alignment points and `\` for line breaks.
```typst
$
  f(x) &= (x + 1)^2 \
       &= x^2 + 2x + 1
$
```

### Function Calls in Math
You can call Typst functions inside math mode using `#`.
```typst
$ #text(fill: blue)[x] + y = 5 $
```
