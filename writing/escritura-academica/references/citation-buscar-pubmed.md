# Búsqueda en PubMed

## Descripción

PubMed se especializa en literatura biomédica y de ciencias de la vida (más de 35 millones de citas). Soporta búsqueda precisa usando términos MeSH y etiquetas de campo.

## Búsqueda Básica

```bash
python scripts/citation-buscar-pubmed.py "Enfermedad de Alzheimer tratamiento" \
  --limit 100 \
  --output alzheimer.json
```

## Consulta Avanzada

### Términos MeSH

MeSH (Medical Subject Headings) proporciona vocabulario controlado.

* Buscar términos en [MeSH Browser](https://meshb.nlm.nih.gov/search).
* Usar en consultas: `"Diabetes Mellitus, Type 2"[MeSH]`.

### Etiquetas de Campo

* `[Title]`: Buscar solo en título.
* `[Title/Abstract]`: Buscar en título o resumen.
* `[Author]`: Buscar por nombre de autor (`"Smith J"[Author]`).
* `[Journal]`: Buscar revista específica.
* `[Publication Date]`: Rango de fechas (`2020:2024[Publication Date]`).
* `[Publication Type]`: Tipo de artículo (`"Review"[Publication Type]`, `"Clinical Trial"[Publication Type]`).

### Ejemplos de Consultas Complejas

```bash
# Ensayos clínicos sobre tratamiento de diabetes publicados recientemente
"Diabetes Mellitus, Type 2"[MeSH] AND "Drug Therapy"[MeSH]
AND "Clinical Trial"[Publication Type] AND 2020:2024[Publication Date]
```