# Research Literature

Contexto del skill `research-literature`: pipeline de descubrimiento de fuentes académicas en español colombiano (es-CO). Busca artículos usando EXA, Semantic Scholar y Google Scholar en cascada. Las fuentes descubiertas se entregan como insumo al skill `generar-paper`, que las valida (Tier C/B) y compone en PDF vía Typst.

## Lenguaje

### Búsqueda y descubrimiento

**Búsqueda en cascada**:
Estrategia de búsqueda que prueba herramientas en orden de preferencia (EXA → Semantic Scholar → Google Scholar), deteniéndose cuando se alcanza un umbral suficiente de resultados. Si una herramienta falla o devuelve pocos resultados, se pasa a la siguiente.
_Evitar_: búsqueda secuencial, waterfall search

**Resultados suficientes**:
Umbral de 5 a 10 fuentes relevantes y diversas (distintos autores, años, venues) que cubren el tema desde múltiples ángulos. Si no se alcanza, se pasa a la siguiente herramienta en la cascada.
_Evitar_: suficientes resultados, enough results

**Descubrimiento de fuentes**:
Proceso de búsqueda e identificación de artículos académicos a partir de un tema de investigación. Incluye la extracción de metadatos básicos (título, autores, año, DOI, URL) pero NO incluye validación de citas. La validación la hace `generar-paper`.
_Evitar_: búsqueda de literatura, literature search

### Herramientas de búsqueda

**EXA**:
Motor de búsqueda semántica con embeddings neuronales. Soporta la categoría `research paper` para filtrar exclusivamente artículos académicos. Requiere API key (`EXA_API_KEY`). SDK: `exa-py`.
_Evitar_: Exa, exa.ai

**Semantic Scholar**:
API REST gratuita de metadatos académicos mantenida por el Allen Institute for AI. Sin API key: 100 req/5 min. Con key (`SEMANTIC_SCHOLAR_API_KEY`): 100 req/seg. Provee metadatos ricos: conteo de citas, venues, campos de estudio, acceso abierto.
_Evitar_: S2, SemScholar

**Google Scholar**:
Buscador académico de Google. Sin API oficial. El agente realiza búsqueda manual usando operadores avanzados (`author:`, `intitle:`, `source:`). Último recurso en la cascada por su falta de estructura y riesgo de CAPTCHA.
_Evitar_: GS, Scholar

### Conceptos compartidos con generar-paper

Los siguientes términos están definidos en `generar-paper/CONTEXT.md`. `research-literature` los consume sin redefinirlos:

- **Fuente formal** — publicación con DOI (artículo, paper, capítulo de libro). Admite validación Tier C en `generar-paper`.
- **Fuente no formal** — publicación sin DOI (web, informe, documentación). Solo admite validación Tier B en `generar-paper`.
- **DOI** — identificador permanente de publicación académica. Clave para la deduplicación y validación de citas.
- **BibTeX** — formato de archivo para almacenar referencias bibliográficas. Ambos scripts de `research-literature` soportan `--format bibtex`.

### Formato de salida

**JSON estructurado**:
Formato estándar de salida de los scripts de búsqueda. Estructura:

```json
{
  "query": "frase de búsqueda",
  "timestamp": "ISO 8601",
  "sources_used": ["exa"],
  "total_results": N,
  "results": [
    {
      "title": "...",
      "authors": ["...", "..."],
      "year": 2024,
      "doi": "10.xxx/...",
      "url": "https://...",
      "source": "exa|semantic_scholar",
      "abstract": "...",
      "citation_count": 42
    }
  ]
}
```

Campos opcionales: `abstract`, `citation_count`, `venue`, `journal`, `fields_of_study`, `open_access_pdf`. La presencia de estos campos depende de la herramienta de búsqueda usada y de la disponibilidad en la API.

**Deduplicación**:
Proceso de combinar resultados de múltiples herramientas eliminando entradas duplicadas. Criterio primario: DOI exacto. Criterio secundario: similitud difusa de título ≥ 0.85. Se conserva la entrada con más metadatos.
_Evitar_: merge, unificar resultados
