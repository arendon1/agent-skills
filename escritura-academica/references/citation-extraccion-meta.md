# Extracción de Metadatos

## Descripción

Convertir identificadores de papers (DOI, PMID, ID arXiv) a metadatos completos y precisos.

## Identificadores Soportados

* **DOI**: Fuente primaria (vía CrossRef).
* **PMID**: Papers biomédicos (vía PubMed).
* **arXiv ID**: Preprints (vía API de arXiv).
* **URL**: Páginas web (metadatos básicos).

## Comandos de Uso

```bash
python scripts/citation-extraccion-meta.py --doi 10.1038/s41586-021-03819-2
python scripts/citation-extraccion-meta.py --pmid 34265844
python scripts/citation-extraccion-meta.py --arxiv 2103.14030
python scripts/citation-extraccion-meta.py --input identifiers.txt --output citations.bib
```

## Fuentes de Metadatos

1. **API de CrossRef**: Mejor para DOIs. Datos del publicador.
2. **E-utilities de PubMed**: Mejor para IDs biomédicos. Incluye términos MeSH.
3. **API de arXiv**: Metadatos completos para preprints.
4. **API de DataCite**: Para datasets y software DOIs.

## Mejores Prácticas

1. **Siempre usar DOIs cuando estén disponibles**: Son permanentes y tienen los mejores metadatos.
2. **Verificar datos extraídos**: Revisar acentos de autores, abreviaturas de revistas.
3. **Manejar Preprints**: Si un preprint es publicado después, actualizar a la versión publicada.
4. **Consistencia**: Mantener formatos de nombres de autores y abreviaturas de revistas consistentes.