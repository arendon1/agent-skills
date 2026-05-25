# Formato BibTeX

## Descripción

Generar entradas BibTeX limpias y correctamente formateadas (`.bib`).

## Tipos de Entrada Comunes

* **@article**: Artículos de revista. Requeridos: author, title, journal, year.
* **@book**: Libros. Requeridos: author/editor, title, publisher, year.
* **@inproceedings**: Papers de conferencia. Requeridos: author, title, booktitle, year.
* **@misc**: Preprints, software, datasets, páginas web.

## Ejemplo de Entradas

```bibtex
@article{Smith2024,
  author  = {Smith, John and Doe, Jane},
  title   = {{The Title with Capitalization Preserved}},
  journal = {Journal of Examples},
  year    = {2024},
  volume  = {10},
  number  = {3},
  pages   = {123--145},
  doi     = {10.1234/example}
}
```

## Reglas de Formato

1. **Claves de Citación**: Usar claves significativas como `FirstAuthorYearKeyword`.
2. **Capitalización**: Proteger acrónimos y nombres propios con llaves: `{CRISPR}`.
3. **Rayos de Página**: Usar rayo doble: `123--145`.
4. **Autores**: Usar `and` para separar: `Author One and Author Two`.
5. **Deduplicación**: Eliminar entradas duplicadas basándose en DOI o Título/Año.

## Comandos de Formateo

```bash
python scripts/citation-formato.py references.bib --output formatted.bib
python scripts/citation-formato.py references.bib --sort key --output sorted.bib
python scripts/citation-formato.py references.bib --deduplicate --output clean.bib
```