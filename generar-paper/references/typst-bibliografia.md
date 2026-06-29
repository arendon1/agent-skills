# Bibliografía en Typst

## Configuración Básica

```typst
Some text with a citation @smith2023.
Multiple citations @jones2024 @doe2025.

#bibliography("references.bib", title: "Referencias", style: "apa")
```

## Estilos de Cita

- `"ieee"` - Estilo numérico [1], [2]
- `"apa"` - Estilo autor-año (Smith, 2023)
- `"chicago-author-date"` - Chicago autor-fecha
- `"chicago-notes"` - Chicago notas y bibliografía
- `"mla"` - Estilo MLA

## Formato BibTeX

```bibtex
@article{smith2023,
  title = {Title of the Article},
  author = {Smith, John and Doe, Jane},
  journal = {Journal Name},
  year = {2023},
  volume = {10},
  pages = {123--145},
  doi = {10.1234/example}
}
```

## Parámetros de la Función Bibliografía

```typst
#bibliography(
  "file.bib",
  title: "Referencias",
  style: "apa",
  full: false,
)