---
name: research-literature
description: |
  Busca artículos académicos y fuentes científicas usando EXA, Semantic Scholar y Google Scholar, con resultados estructurados para citar en papers. Usa cuando el usuario necesite encontrar fuentes para un paper o ensayo, revisar el estado del arte de un tema, preparar una revisión de literatura, o diga "busca papers sobre...", "encuentra artículos de...", "qué investigaciones hay sobre...", "fuentes para mi paper".
invocation: auto
layer: domain
provides: [academic-search]
language: es-CO
metadata:
  version: "1.2.0"
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

> **Atajo desde el coding-agent:** cuando el agente corre dentro de un
> coding-agent que tenga cargada una extensión de búsqueda con EXA (por
> ejemplo la tool `exa_search`), prefiere esa tool sobre este script —
> misma API, menos boilerplate, cancelable desde el agente. El script sigue
> siendo el path canónico para flujos batch fuera del agente.

## Workflow

### 1. Recibir consulta

El usuario entrega un tema de investigación, idealmente con filtros:
- Rango de fechas (`--start-published-date`, `--end-published-date`)
- Dominios o venues específicos (`--include-domains`)
- Categoría de fuente (`--category`, default `research paper`)
- Mínimo de citas

### 2. Ejecutar búsqueda (en cascada)

#### EXA (prioridad 1)

script: `search_exa.py` — usa `exa-py >= 2.x` y los endpoints modernos
(`Exa.search`, `Exa.find_similar`, `Exa.get_contents`, `Exa.answer`).
Los antiguos `search_and_contents` / `find_similar_and_contents` están
deprecados en exa-py 2.x.

`search_exa.py` expone cuatro acciones vía `--action`:

| Acción | Uso | Argumentos clave |
|--------|-----|------------------|
| `search` (default) | Búsqueda semántica con filtros finos | `--query`, `--include-domains`, `--category`, `--start-published-date`, `--type` |
| `similar` | "Más papers como este" (citation snowball) | `--url`, `--category`, `--limit` |
| `contents` | Fetch del texto completo de uno o más URLs/DOIs | `--url` o `--urls`, `--max-characters` |
| `answer` | Q&A grounded con citas | `--question`, `--model`, `--full-text` |

```bash
# Búsqueda semántica con filtros finos
python scripts/search_exa.py --action=search \
  "transformer attention interpretability" \
  --limit 15 --category "research paper" \
  --start-published-date 2024-01-01 \
  --include-domains arxiv.org,aclanthology.org \
  --full-text

# Citation snowball a partir de un paper conocido
python scripts/search_exa.py --action=similar \
  --url "https://arxiv.org/abs/1706.03762" \
  --category "research paper" --limit 10

# Fetch del texto completo de un DOI para verificación
python scripts/search_exa.py --action=contents \
  --url "https://doi.org/10.48550/arxiv.2310.16270" \
  --max-characters 8000

# Q&A grounded (cite-fuentes)
python scripts/search_exa.py --action=answer \
  --question "What is the Globant AI Pods subscription model?"

# Salida BibTeX
python scripts/search_exa.py --action=search \
  "neural rendering" --format bibtex --output referencias.bib
```

Requiere: `EXA_API_KEY` en variable de entorno. Ver
`references/buscar-exa.md` para la lista completa de filtros y estrategias
de query.

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
  "action": "search",
  "timestamp": "2026-08-20T10:30:00",
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
      "source": "exa"
    }
  ]
}
```

Para salidas de `--action=answer`, el JSON incluye además `answer` (string)
y `citations[]` (cada cita con la misma forma que un result).

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
| `references/buscar-exa.md` | Guía de búsqueda con EXA: filtros, categorías, estrategias de query, decisiones de `--action` |
| `references/buscar-semantic-scholar.md` | Guía de búsqueda con Semantic Scholar: endpoints, filtros, campos disponibles |
| `references/buscar-google-scholar.md` | Estrategia de búsqueda manual en Google Scholar: operadores, filtros, tácticas |
| `references/estrategia-busqueda.md` | Estrategia general: cuál herramienta usar, cuándo, y cómo combinarlas |

## Scripts

| Script | Propósito |
|--------|----------|
| `scripts/search_exa.py` | Búsqueda con EXA API vía `exa-py >= 2.x`. Cuatro acciones (`search`/`similar`/`contents`/`answer`). |
| `scripts/search_semantic_scholar.py` | Búsqueda con Semantic Scholar API REST |
| `scripts/merge_results.py` | Combinar y deduplicar resultados de múltiples fuentes |

## Dependencias

- **Python 3.10+** — para todos los scripts
- **`exa-py >= 2.x`** — SDK de Python para EXA API (`pip install 'exa-py>=2.0'`)
- **`requests`** — para Semantic Scholar API (`pip install requests`)

## Habilidades complementarias

- **`generar-paper`** — validar citas y componer documentos. Cargar después de obtener fuentes con este skill.
- **`find-docs`** — consultar documentación actualizada de EXA, Semantic Scholar, o APIs relacionadas.
