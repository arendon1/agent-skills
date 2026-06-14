---
name: generar-paper
description: >-
  Genera documentos académicos en formato APA 7 (estudiante) con validación estricta de
  citas y salida en PDF vía Typst. Usa cuando el usuario necesita validar referencias,
  formatear bibliografía, componer un paper con estructura IMRaD, o compilar un documento
  académico a PDF.
language: es-CO
metadata:
  version: "2.0.0"
  trit: 0
  risk_tier: CAUTION
---

# Generar Paper

## Propósito

Pipeline de validación de citas y composición tipográfica para documentos académicos
en español colombiano (es-CO). Recibe fuentes ya identificadas (DOI, PMID, arXiv, URL)
y produce un PDF con formato APA 7 para estudiante usando Typst.

**Este skill no busca fuentes.** La búsqueda y descubrimiento de artículos se hace con
el skill `research-literature`. Este skill asume que las fuentes ya están identificadas
y se enfoca en validarlas rigurosamente y componer el documento final.

**Cualquier cita rota, falsa o alucinada es un error catastrófico.**

## Arquitectura

```
Fuentes (DOI/PMID/arXiv/URL) → Extraer metadatos → Validar (Tier C → B) → Formatear BibTeX → Componer Typst → Compilar PDF
```

### Niveles de Verificación de Citas

| Nivel | Descripción | Aplica a |
|-------|-------------|----------|
| **Tier C** | Abre la fuente, extrae título, autores y año, y los compara contra la entrada BibTeX (coincidencia difusa para título, exacta para año, parcial para autores) | Fuentes con DOI |
| **Tier B** | Verifica que la URL resuelve (HTTP 200) y el título de la página coincide | Fuentes sin DOI (webs, informes, docs técnicas) |

Ver `docs/adr/0001-verificacion-citas-tier-c.md` para la decisión de arquitectura.

## Workflow

### 1. Recibir fuentes

El usuario o el skill `research-literature` entregan identificadores: DOI, PMID,
arXiv ID, o URL. También se aceptan archivos BibTeX existentes.

### 2. Extraer metadatos

Convertir cada identificador a una entrada BibTeX estructurada:

- script: `extract_metadata.py` — soporta DOI (CrossRef), PMID (PubMed), arXiv ID, y URL
- script: `doi_to_bibtex.py` — conversión rápida de DOI a BibTeX vía CrossRef

### 3. Validar citas

Ejecutar verificación de contenido (Tier C) con fallback a resolución (Tier B):

script: `validate_citations.py` — valida archivos BibTeX completos.

```bash
# Validación completa con verificación de contenido
python scripts/validate_citations.py references.bib --check-dois

# Solo validación estructural (formato, campos requeridos, duplicados)
python scripts/validate_citations.py references.bib
```

Reglas críticas:
- **Nunca** incluir una cita sin validar
- Cualquier discrepancia de título o año es **error catastrófico**
- Las discrepancias de autores son **advertencia** (requieren revisión manual)
- Para fuentes sin DOI, verificar que la URL esté viva y el título coincida

### 4. Formatear BibTeX

Limpiar, ordenar y deduplicar el archivo de referencias:

script: `format_bibtex.py`

```bash
python scripts/format_bibtex.py references.bib --deduplicate --sort year
```

### 5. Componer en Typst

Generar código Typst siguiendo las guías de referencia:

- `references/imrad-guia.md` — estructura IMRaD y estilo APA 7
- `references/typst-scripting.md` — sintaxis Typst, lógica, estado
- `references/typst-calculo.md` — modo matemático y ecuaciones
- `references/typst-graficos.md` — gráficos con CeTZ
- `references/typst-layout.md` — formato de página APA 7
- `references/typst-data.md` — carga de datos externos (CSV, JSON)
- `references/typst-paquetes.md` — paquetes populares de Typst
- `references/typst-bibliografia.md` — integración de bibliografía con `cite()`

Plantilla de ejemplo: `examples/paper-apa.typ` — usa el paquete `versatile-apa:7.2.0`
en formato estudiante con localización en español.

### 6. Compilar a PDF

Compilar el documento Typst y validar la salida:

script: `compile.py`

```bash
python scripts/compile.py paper.typ --output paper.pdf
```

El script verifica que:
- Typst esté instalado (`typst --version`)
- La compilación termine sin errores
- El PDF generado sea válido (existe y tiene tamaño > 0)
- No haya referencias rotas en la bibliografía

### 7. Verificación final

Antes de entregar el documento:
- Confirmar que todas las citas en el texto aparecen en la bibliografía
- Verificar que el PDF cumple visualmente con APA 7
- Validar que no hay advertencias pendientes del paso 3

## Referencias

| Guía | Propósito |
|------|----------|
| `references/imrad-guia.md` | Estructura IMRaD, estilo APA 7, voz y tiempo verbal |
| `references/diseno-investigacion.md` | Preguntas de investigación (FINER), ética |
| `references/citation-extraccion-meta.md` | Extracción de metadatos desde DOI/PMID/arXiv/URL |
| `references/citation-validacion.md` | Validación estructural de citas |
| `references/citation-verificacion-contenido.md` | Verificación Tier C: comparación de contenido |
| `references/citation-formato-bibtex.md` | Formateo, limpieza y deduplicación de BibTeX |
| `references/typst-scripting.md` | Sintaxis Typst, lógica, estado |
| `references/typst-calculo.md` | Modo matemático y ecuaciones |
| `references/typst-graficos.md` | Gráficos con CeTZ |
| `references/typst-paquetes.md` | Paquetes populares de Typst |
| `references/typst-layout.md` | Layout, páginas, grids |
| `references/typst-data.md` | Carga de datos externos (CSV, JSON) |
| `references/typst-bibliografia.md` | Bibliografía y cite() |

## Scripts

| Script | Propósito |
|--------|----------|
| `scripts/extract_metadata.py` | Extraer metadatos desde DOI, PMID, arXiv ID o URL |
| `scripts/doi_to_bibtex.py` | Convertir DOI a BibTeX vía CrossRef |
| `scripts/validate_citations.py` | Validar citas (Tier C con fallback a Tier B) |
| `scripts/format_bibtex.py` | Formatear, limpiar, ordenar y deduplicar BibTeX |
| `scripts/compile.py` | Compilar documento Typst a PDF con validación |

## Dependencias

- **Typst** — lenguaje de composición tipográfica. Verificar con `typst --version`
- **Python 3.10+** — para todos los scripts del pipeline
- **Paquetes Typst** — `versatile-apa:7.2.0`, `cetz:0.4.1` (se descargan automáticamente al compilar)

## Domain Context

Ver `CONTEXT.md` para el glosario de términos del dominio (validación por contenido,
fuente formal, formato estudiante, etc.).

Ver `docs/adr/` para las decisiones de arquitectura registradas.
