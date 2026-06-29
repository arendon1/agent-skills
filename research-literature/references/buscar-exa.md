# Buscar con EXA

Guía de búsqueda académica usando el motor de búsqueda semántica EXA.
EXA usa embeddings neuronales para entender el significado de la consulta,
no solo palabras clave. Especialmente efectivo para investigación científica
porque soporta la categoría `research paper`.

## Requisitos

- **API key:** `EXA_API_KEY` en variable de entorno. Obtener en https://exa.ai
- **SDK:** `pip install exa-py`

## Cuándo usar EXA

- Búsqueda semántica: el usuario describe un concepto, no solo palabras clave
- Necesidad de alta precisión y relevancia en los resultados
- Búsqueda en dominios específicos (arxiv.org, dl.acm.org, nature.com)
- Cuando Semantic Scholar devuelve resultados muy genéricos o irrelevantes

## Filtros disponibles

| Filtro | Flag | Descripción |
|--------|------|-------------|
| Rango de años | `--start-year`, `--end-year` | Filtra por año de publicación |
| Dominios | `--domains` | Limita a dominios específicos (separados por coma) |
| Autor | `--author` | Filtra por autor (agrega `author:` al query) |
| Título | `--title-contains` | Filtra por palabras en el título (`intitle:`) |
| Límite | `--limit` | Número máximo de resultados (default: 10) |

## Estrategias de búsqueda

### 1. Búsqueda semántica amplia

Para explorar un tema sin filtros muy restrictivos:

```bash
python scripts/search_exa.py "deep learning for medical image segmentation" --limit 15
```

### 2. Búsqueda enfocada por dominio

Cuando se necesita literatura de un campo o venue específico:

```bash
python scripts/search_exa.py "transformer architectures for NLP" \
  --domains arxiv.org,aclanthology.org \
  --limit 20
```

### 3. Búsqueda por autor y tema

Para encontrar trabajos de un investigador específico:

```bash
python scripts/search_exa.py "reinforcement learning" \
  --author "Sutton" \
  --start-year 2018
```

### 4. Ventana temporal reciente

Para estados del arte o revisiones actualizadas:

```bash
python scripts/search_exa.py "large language model safety" \
  --start-year 2024 --end-year 2025 \
  --limit 25
```

## Salida

### JSON (default)

Archivo JSON con estructura estándar: `query`, `timestamp`, `sources_used`, `total_results`, `results[]`.
Cada resultado incluye: `title`, `authors`, `year`, `doi`, `url`, `abstract`, `source`.

### BibTeX

```bash
python scripts/search_exa.py "graph neural networks" --format bibtex --output refs.bib
```

Genera un archivo `.bib` con entradas `@article` listas para usar en `generar-paper`.

## Notas

- La categoría `research paper` está fija en el script. Para otros tipos de contenido,
  modificar el parámetro `category` en `search_exa.py`.
- EXA soporta `includeText` para obtener fragmentos relevantes del texto completo,
  lo que permite verificar citas con más contexto.
- Rate limits: consultar la documentación actualizada de `exa-py` con find-docs.
