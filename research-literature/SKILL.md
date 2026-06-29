---
name: research-literature
description: >-
  Busca artículos académicos usando EXA, Semantic Scholar y Google Scholar.
  Usa cuando el usuario necesita encontrar fuentes para un paper, revisar
  literatura, o dice "busca papers sobre...", "encuentra artículos de...",
  "qué investigaciones hay sobre...".
invocation: auto
layer: domain
provides: [academic-search]
language: es-CO
metadata:
  version: "1.1.0"
  trit: 0
  risk_tier: CAUTION
---

# Research Literature

## Propósito

Skill de descubrimiento de fuentes académicas. Recibe un tema de investigación
y devuelve fuentes identificadas con metadatos estructurados (DOI, PMID, URL, autores,
año, resumen). Las fuentes descubiertas se entregan como insumo al skill `generar-paper`,
que se encarga de validarlas, formatearlas y componer el documento final.

**Este skill no valida citas ni compone documentos.** Solo busca y descubre. La
validación rigurosa la hace `generar-paper` con su pipeline de verificación Tier C.

## Arquitectura

```
Tema de investigación → [EXA → Semantic Scholar → Google Scholar] → Fuentes estructuradas → generar-paper
```

El pipeline de búsqueda es **en cascada**, por orden de preferencia:

| Prioridad | Herramienta | Fortaleza |
|-----------|------------|-----------|
| 1 | **EXA** | Búsqueda semántica con embeddings, alta precisión, filtra por categoría `research paper` |
| 2 | **Semantic Scholar** | API gratuita, metadatos ricos (citas, venues, campos de estudio), sin API key requerida |
| 3 | **Google Scholar** | Cobertura máxima, sin API (búsqueda manual guiada por estrategia documentada) |

El agente debe intentar EXA primero. Si no hay API key o los resultados son insuficientes,
pasa a Semantic Scholar. Google Scholar es el último recurso para búsqueda manual.

## Workflow

### 1. Recibir consulta

El usuario entrega un tema de investigación, idealmente con filtros:
- Rango de años (`--start-year`, `--end-year`)
- Dominios o venues específicos
- Tipo de publicación (artículo, review, conference paper)
- Mínimo de citas

### 2. Ejecutar búsqueda (en cascada)

#### EXA (prioridad 1)

script: `search_exa.py`

```bash
# Búsqueda semántica básica
python scripts/search_exa.py "machine learning in healthcare" --limit 10

# Con filtros de año y dominio
python scripts/search_exa.py "transformer attention mechanisms" \
  --start-year 2020 --end-year 2025 \
  --domains arxiv.org --limit 20 \
  --output resultados.json

# Salida en BibTeX
python scripts/search_exa.py "neural rendering" --format bibtex --output referencias.bib
```

Requiere: `EXA_API_KEY` en variable de entorno.

#### Semantic Scholar (prioridad 2)

script: `search_semantic_scholar.py`

```bash
# Búsqueda por palabra clave
python scripts/search_semantic_scholar.py "coral reef conservation" --limit 20

# Con filtros de año, venue y tipo de publicación
python scripts/search_semantic_scholar.py "quantum error correction" \
  --year 2022-2025 \
  --venue "Nature|Science|Physical Review" \
  --publication-types JournalArticle \
  --min-citations 10 \
  --output papers.json

# Búsqueda por título (útil para verificar si un paper existe)
python scripts/search_semantic_scholar.py --match "Attention Is All You Need"
```

No requiere API key (rate limit: 100 req/5 min sin key). Con `SEMANTIC_SCHOLAR_API_KEY`
el límite sube a 100 req/seg.

#### Google Scholar (prioridad 3)

Sin script. El agente realiza búsqueda manual guiada por la estrategia documentada
en `references/buscar-google-scholar.md`. Usar operadores `author:`, `intitle:`,
`source:` y filtros por año. Google Scholar es el último recurso cuando las APIs
no devuelven resultados suficientes.

### 3. Entregar fuentes

Cuando se usan múltiples herramientas, combinar los resultados con `merge_results.py`
para eliminar duplicados antes de entregar a `generar-paper`:

```bash
python scripts/merge_results.py exa_results.json semantic_results.json \
  --output unified.json
```

El skill produce un archivo JSON estructurado con las fuentes encontradas:

```json
{
  "query": "machine learning in healthcare",
  "timestamp": "2026-06-14T10:30:00",
  "sources_used": ["exa", "semantic_scholar"],
  "total_results": 25,
  "results": [
    {
      "title": "Deep Learning for Healthcare: Review, Opportunities and Challenges",
      "authors": ["Smith, John", "Doe, Jane"],
      "year": 2024,
      "doi": "10.1000/xyz123",
      "url": "https://doi.org/10.1000/xyz123",
      "abstract": "This paper reviews...",
      "source": "exa",
      "citation_count": 42
    }
  ]
}
```

### 4. Integración con generar-paper

El skill `research-literature` entrega fuentes identificadas (DOIs, URLs, metadatos).
El skill `generar-paper` las recibe y ejecuta su pipeline:
extracción → validación Tier C → formateo BibTeX → composición Typst → PDF.

**El agente carga ambos skills juntos** cuando el usuario pide buscar fuentes Y generar
un paper. La orquestación es a nivel de agente, no de código. Ver `references/estrategia-busqueda.md`
para el flujo de integración.

## Referencias

| Guía | Propósito |
|------|----------|
| `references/buscar-exa.md` | Guía de búsqueda con EXA: filtros, categorías, estrategias de query |
| `references/buscar-semantic-scholar.md` | Guía de búsqueda con Semantic Scholar: endpoints, filtros, campos disponibles |
| `references/buscar-google-scholar.md` | Estrategia de búsqueda manual en Google Scholar: operadores, filtros, tácticas |
| `references/estrategia-busqueda.md` | Estrategia general: cuál herramienta usar, cuándo, y cómo combinarlas |

## Scripts

| Script | Propósito |
|--------|----------|
| `scripts/search_exa.py` | Búsqueda semántica con EXA API vía `exa-py` |
| `scripts/search_semantic_scholar.py` | Búsqueda con Semantic Scholar API REST |
| `scripts/merge_results.py` | Combinar y deduplicar resultados de múltiples fuentes |

## Dependencias

- **Python 3.10+** — para todos los scripts
- **`exa-py`** — SDK de Python para EXA API (`pip install exa-py`)
- **`requests`** — para Semantic Scholar API (`pip install requests`)

## Habilidades complementarias

- **`generar-paper`** — validar citas y componer documentos. Cargar después de obtener fuentes con este skill.
- **`find-docs`** — consultar documentación actualizada de EXA, Semantic Scholar, o APIs relacionadas.
