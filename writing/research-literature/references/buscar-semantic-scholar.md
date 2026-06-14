# Buscar con Semantic Scholar

Guía de búsqueda académica usando la API REST gratuita de Semantic Scholar.
Proporciona metadatos ricos (autores, citas, venues, campos de estudio, acceso abierto)
sin requerir API key para uso básico.

## Requisitos

- **Sin API key** para 100 req/5 min. Con `SEMANTIC_SCHOLAR_API_KEY` sube a 100 req/seg.
- **Python:** `requests` (instalar con `pip install requests`)

## Cuándo usar Semantic Scholar

- No hay API key de EXA disponible
- Se necesitan metadatos ricos: conteo de citas, venues, campos de estudio
- Búsqueda por campos de estudio específicos (`fieldsOfStudy`)
- Verificar si un paper existe por coincidencia de título (`--match`)
- Filtrar por tipo de publicación (JournalArticle, Review, Conference)

## Endpoints usados

| Endpoint | Uso | Flag |
|----------|-----|------|
| `GET /paper/search` | Búsqueda por palabra clave | Modo por defecto |
| `GET /paper/search/match` | Coincidencia exacta de título | `--match` |

## Filtros disponibles

| Filtro | Flag | Descripción |
|--------|------|-------------|
| Año | `--year` | Rango (2020-2025) o año único (2024) |
| Venue | `--venue` | Filtrar por venue/jornal (usa `\|` para múltiples) |
| Campos de estudio | `--fields-of-study` | ej: `Computer Science\|Medicine` |
| Tipos de publicación | `--publication-types` | `JournalArticle`, `Review`, `Conference` |
| Mínimo de citas | `--min-citations` | Umbral de citas recibidas |
| Límite | `--limit` | Máximo 100 resultados |

## Campos disponibles en la respuesta

Cada paper incluye: `title`, `authors` (array con `name`, `authorId`), `year`, `venue`,
`publicationDate`, `abstract`, `externalIds` (DOI, PMID, etc.), `url`, `citationCount`,
`fieldsOfStudy`, `journal` (name, volume, pages), `openAccessPdf`, `publicationTypes`.

## Estrategias de búsqueda

### 1. Búsqueda por palabra clave con filtros combinados

```bash
python scripts/search_semantic_scholar.py "coral reef bleaching climate change" \
  --year 2020-2025 \
  --fields-of-study "Environmental Science|Biology" \
  --publication-types JournalArticle \
  --min-citations 5 \
  --limit 30
```

### 2. Búsqueda por venue de prestigio

Para encontrar papers en revistas o conferencias específicas:

```bash
python scripts/search_semantic_scholar.py "quantum error correction" \
  --venue "Nature|Science|Physical Review Letters" \
  --year 2022-2025 \
  --limit 20
```

### 3. Verificación por título

Para confirmar si un paper existe (útil durante la validación Tier C de `generar-paper`):

```bash
python scripts/search_semantic_scholar.py --match "Attention Is All You Need"
```

Retorna papers cuyo título coincide (parcial o totalmente) con el texto dado.

### 4. Búsqueda exploratoria por campo de estudio

```bash
python scripts/search_semantic_scholar.py "transfer learning" \
  --fields-of-study "Computer Science" \
  --publication-types Review \
  --limit 15
```

## Salida

Igual que EXA: JSON estructurado con `query`, `timestamp`, `sources_used`, `total_results`,
`results[]`. Campos adicionales: `citation_count`, `venue`, `journal`, `fields_of_study`,
`open_access_pdf`.

### BibTeX

```bash
python scripts/search_semantic_scholar.py "graph neural networks" \
  --format bibtex --output refs.bib
```

## Notas

- El límite máximo por request es 100. Para búsquedas más grandes, hacer múltiples
  requests paginando con `offset`.
- La API de Semantic Scholar está en beta perpetua. Verificar cambios en la
  documentación oficial con `find-docs`.
- Sin API key, el rate limit es 100 requests por cada 5 minutos. El script no
  implementa rate limiting automático; si se excede, la API retorna HTTP 429.
- Los DOIs se extraen de `externalIds.DOI`. No todos los papers tienen DOI registrado
  en Semantic Scholar.
