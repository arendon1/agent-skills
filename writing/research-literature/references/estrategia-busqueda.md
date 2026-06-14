# Estrategia de búsqueda

Guía para el agente: qué herramienta usar, cuándo, y cómo combinar resultados de
múltiples fuentes en una búsqueda de literatura académica.

## Principio de cascada

El agente debe seguir este orden, deteniéndose cuando los resultados sean suficientes:

```
EXA → Semantic Scholar → Google Scholar
```

**Suficiente** significa: al menos 5-10 fuentes relevantes y diversas que cubran
el tema desde distintos ángulos (autores, años, venues). Si no se alcanza este
umbral, pasar a la siguiente herramienta.

## Árbol de decisión

```
¿Tiene EXA_API_KEY?
├── Sí → Empezar con EXA
│   ├── ¿Resultados suficientes? → Entregar
│   └── No → Semantic Scholar
│       ├── ¿Resultados suficientes? → Entregar
│       └── No → Google Scholar → Entregar
└── No → Empezar con Semantic Scholar
    ├── ¿Resultados suficientes? → Entregar
    └── No → Google Scholar → Entregar
```

## Cuándo usar cada herramienta

### EXA

**Fortalezas:**
- Búsqueda semántica: entiende el significado, no solo keywords
- Alta precisión en categoría `research paper`
- Filtro por dominios (arxiv.org, dl.acm.org, etc.)
- Bueno para búsquedas conceptuales ("impacto de la IA en la educación médica")

**Debilidades:**
- Requiere API key y créditos
- Rate limits más restrictivos que Semantic Scholar
- Menos metadatos (sin conteo de citas, campos de estudio)

**Usar cuando:**
- La consulta es conceptual o abstracta
- Se necesita filtrar por dominios específicos
- Semantic Scholar devuelve resultados muy ruidosos

### Semantic Scholar

**Fortalezas:**
- Sin API key para uso básico
- Metadatos ricos: citas, venues, campos de estudio, acceso abierto
- Filtro por tipo de publicación, venue, campos de estudio
- Verificación por título (`--match`)

**Debilidades:**
- Búsqueda por keyword menos precisa que EXA para conceptos abstractos
- Cobertura menor que Google Scholar (no indexa todo)
- Límite de 100 resultados por request

**Usar cuando:**
- No hay API key de EXA
- Se necesitan metadatos ricos para filtrar
- Se requiere verificar un paper por título
- Búsqueda con filtros de venue o campo de estudio

### Google Scholar

**Fortalezas:**
- Cobertura máxima: tesis, patentes, libros, literatura gris
- Búsqueda de citas (cited by)
- Perfiles de autor

**Debilidades:**
- Sin API: búsqueda manual, lenta, inconsistente
- Metadatos pobres (sin abstract, DOI no siempre visible)
- Riesgo de CAPTCHA
- Resultados menos estructurados

**Usar cuando:**
- EXA y Semantic Scholar no devuelven suficientes resultados
- Tema muy específico o de nicho
- Se necesita literatura gris (tesis, informes técnicos)
- Búsqueda de citas de un paper específico

## Combinación de fuentes

### Caso 1: Búsqueda estándar

```
EXA (10 resultados) + Semantic Scholar (10 resultados)
→ Unir, deduplicar por DOI, entregar
```

### Caso 2: Sin API key de EXA

```
Semantic Scholar (20 resultados)
→ Si insuficiente, Google Scholar (manual, 5-10 resultados)
→ Unir, deduplicar, entregar
```

### Caso 3: Tema muy específico

```
EXA (pocos resultados) → Semantic Scholar (complementar)
→ Google Scholar (buscar tesis, preprints, literatura gris)
→ Unir, deduplicar, entregar
```

## Deduplicación

Al combinar resultados de múltiples fuentes:

1. **Por DOI**: si dos resultados comparten DOI, son el mismo paper. Conservar la
   entrada con más metadatos (típicamente Semantic Scholar).
2. **Por título**: si los títulos tienen similitud > 0.90 (difusa), probablemente
   son el mismo paper. Conservar la entrada con DOI.
3. **Marcar fuente original**: mantener el campo `source` de la fuente que proveyó
   la entrada principal. Agregar `"also_found_in": ["semantic_scholar"]` si apareció
   en múltiples fuentes.

## Integración con generar-paper

1. `research-literature` entrega un JSON con fuentes identificadas
2. El agente pasa ese JSON a `generar-paper`:
   - `generar-paper` usa `extract_metadata.py` para obtener BibTeX desde los DOIs
   - `generar-paper` ejecuta validación Tier C sobre cada fuente
   - Si alguna fuente falla la validación, el agente puede volver a buscar con
     `research-literature` usando términos ajustados
3. `generar-paper` continúa con formateo BibTeX → composición Typst → PDF

### Flujo de ida y vuelta

```
research-literature → fuentes.json
  → generar-paper: extract_metadata → validate_citations
    → ¿Citas válidas?
      ├── Sí → format_bibtex → compile → PDF ✅
      └── No → research-literature: re-buscar fuentes alternativas
```

## Recomendaciones para el agente

1. **Siempre verificar el DOI** de cada fuente antes de entregarla. Si una fuente de
   EXA o Semantic Scholar no tiene DOI, marcarla como `"doi": null` para que
   `generar-paper` aplique validación Tier B.
2. **Prefiere fuentes con DOI y alto conteo de citas.** Son más fáciles de validar
   y tienen mayor probabilidad de ser legítimas.
3. **Diversidad de fuentes:** no entregar 15 papers del mismo autor o venue. Si los
   resultados son homogéneos, ajustar los filtros (quitar `--domains`, reducir
   `--min-citations`, ampliar rango de años).
4. **Transparencia:** informar al usuario qué herramientas se usaron y cuántos
   resultados aportó cada una. Si se usó Google Scholar, advertir que los metadatos
   pueden ser menos precisos.
5. **Idempotencia:** la misma búsqueda con los mismos filtros debe producir
   resultados consistentes. Si el usuario pide refinar, ajustar los filtros,
   no solo repetir la búsqueda.
