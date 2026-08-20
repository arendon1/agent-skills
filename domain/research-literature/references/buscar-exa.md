# Buscar con EXA

Guía de búsqueda académica usando el motor de búsqueda semántica EXA.
EXA usa embeddings neuronales para entender el significado de la consulta,
no solo palabras clave. El script `search_exa.py` expone cuatro acciones
que mapean 1:1 a los endpoints REST de EXA.

## Requisitos

- **API key:** `EXA_API_KEY` en variable de entorno. Obtener en https://exa.ai
- **SDK:** `exa-py >= 2.x` (`pip install 'exa-py>=2.0'`)
- El script usa la API moderna (`Exa.search`, `Exa.find_similar`,
  `Exa.get_contents`, `Exa.answer`). Los nombres antiguos están deprecados.

## Cuándo usar EXA

- Búsqueda semántica: el usuario describe un concepto, no solo palabras clave.
- Necesidad de alta precisión y relevancia en los resultados.
- Búsqueda en dominios específicos (`arxiv.org`, `dl.acm.org`, `nature.com`).
- Cuando Semantic Scholar devuelve resultados muy genéricos o irrelevantes.
- Cuando necesitas **traer el texto completo de un paper** (acción `contents`)
  o **una respuesta sintetizada con citas** (acción `answer`).

## Acciones disponibles (`--action`)

| Acción | Endpoint EXA | Caso de uso |
|--------|--------------|-------------|
| `search` (default) | `POST /search` | Búsqueda semántica con filtros finos |
| `similar` | `POST /findSimilar` | "Papers como este" — citation snowball desde una URL conocida |
| `contents` | `POST /contents` | Fetch del texto completo por URL(s) — útil para verificar un paper |
| `answer` | `POST /answer` | Q&A grounded con citas devueltas |

## Filtros disponibles

Compartidos entre `search` y (en subconjunto) `similar`:

| Filtro | Flag | Descripción |
|--------|------|-------------|
| Categoría | `--category` | `research paper` (default), `news`, `company`, `github`, `pdf`, ... |
| Tipo de búsqueda | `--type` | `auto`, `instant`, `neural`, `fast`, `deep`, `deep-reasoning` |
| Rango de publicación | `--start-published-date`, `--end-published-date` | ISO `YYYY-MM-DD` |
| Rango de crawl | `--start-crawl-date`, `--end-crawl-date` | Cuándo EXA indexó la página |
| Whitelist dominios | `--include-domains` | CSV, ej. `arxiv.org,nature.com` |
| Blacklist dominios | `--exclude-domains` | CSV |
| Filtro de contenido | `--include-text` | CSV — strings que DEBEN aparecer en la página |
| Filtro de contenido | `--exclude-text` | CSV — strings que NO deben aparecer |
| Autor | `--author` | Se agrega `author:` al query (search) |
| Título contiene | `--title-contains` | Se agrega `intitle:` al query (search) |
| Queries alternativos (deep) | `--additional-queries` | Separados por `\|` — max 5 |
| Localización usuario | `--user-location` | ISO 2 letras, ej. `US` |
| System prompt | `--system-prompt` | Guía el LLM de síntesis |

Forma de la página (todos):

| Forma | Flag | Uso |
|-------|------|-----|
| Full text | `--full-text` | Trae el texto completo. Usar `--max-characters` para acotar (default 5000). |
| Highlights | `--highlights` | Frases relevantes (más barato que full text) |
| Summary | `--summary` | Resumen generado por LLM por página |

## Estrategias de búsqueda

### 1. Búsqueda semántica amplia (`action=search`)

Para explorar un tema sin filtros restrictivos:

```bash
python scripts/search_exa.py --action=search \
  "deep learning for medical image segmentation" --limit 15
```

### 2. Búsqueda enfocada por dominio y ventana temporal

```bash
python scripts/search_exa.py --action=search \
  "transformer architectures for NLP" \
  --include-domains arxiv.org,aclanthology.org \
  --start-published-date 2024-01-01 --limit 20
```

### 3. Búsqueda por autor y tema

```bash
python scripts/search_exa.py --action=search \
  "reinforcement learning" \
  --author "Sutton" --start-published-date 2018
```

### 4. Estado del arte reciente con full text

Para revisiones de literatura donde se necesita el texto completo:

```bash
python scripts/search_exa.py --action=search \
  "large language model safety" \
  --start-published-date 2024-01-01 \
  --end-published-date 2025-12-31 \
  --limit 25 --full-text --max-characters 8000
```

### 5. Citation snowball (`action=similar`)

Cuando ya tenés un paper clave y querés ampliar la red de citas:

```bash
python scripts/search_exa.py --action=similar \
  --url "https://arxiv.org/abs/1706.03762" \
  --category "research paper" --limit 15
```

### 6. Fetch por URL conocida (`action=contents`)

Para verificar una cita o extraer el abstract completo de un DOI:

```bash
python scripts/search_exa.py --action=contents \
  --url "https://doi.org/10.48550/arxiv.2310.16270" \
  --max-characters 8000
```

### 7. Respuesta sintetizada con citas (`action=answer`)

Q&A grounded — el LLM de EXA devuelve una respuesta más un array de citas
verificables. Útil para resúmenes ejecutivos o preguntas rápidas.

```bash
python scripts/search_exa.py --action=answer \
  --question "What is the Globant AI Pods subscription model?" \
  --model exa-pro
```

## Salida

### JSON (default)

```json
{
  "query": "...",
  "action": "search",
  "timestamp": "2026-08-20T...",
  "sources_used": ["exa"],
  "total_results": 15,
  "results": [
    {
      "title": "...",
      "authors": ["..."],
      "year": 2024,
      "doi": "10.xxx/yyy",
      "url": "https://...",
      "abstract": "...",
      "source": "search"
    }
  ]
}
```

Para `--action=answer`, el JSON además incluye `answer` (string) y las
citas en `results[]` con `source: "answer"`.

El shape de cada `results[]` entry es **estable y compatible con
`merge_results.py`** y con `generar-paper`.

### BibTeX

```bash
python scripts/search_exa.py --action=search \
  "graph neural networks" --format bibtex --output refs.bib
```

Genera un archivo `.bib` con entradas `@article` listas para usar en
`generar-paper`. Funciona también con `--action=similar` (mismo shape).

## Decisión rápida: ¿qué `--action` uso?

```
¿Tengo el URL / DOI del paper?
├── Sí, quiero el texto completo   → contents
├── Sí, quiero papers parecidos    → similar
└── No
    ├── ¿Quiero una respuesta
    │   sintetizada con citas?      → answer
    └── No, quiero los resultados
        crudos con filtros           → search (default)
```

## Notas

- EXA soporta `contents.text.max_characters` para acotar el texto devuelto
  — siempre pasar `--max-characters` en `--full-text` para no inflar el JSON.
- Para mejorar la calidad de búsqueda en `search`, combiná `--include-domains`
  + `--start-published-date` + `--category research paper`. Es la combinación
  más estable para literatura académica.
- El campo `output_schema` de la API EXA no está expuesto por este script;
  el uso típico aquí no requiere JSON estructurado. Si lo necesitás, usá
  directamente la tool `exa_search` de la extensión `exa-search` (cuando el
  coding-agent la tenga cargada), que sí lo soporta.
- Rate limits: consultar la documentación actualizada de `exa-py` con `find-docs`.
