---
name: escritura-academica
description: >-
  Produce documentos académicos listos para publicación en formato APA 7 usando Typst.
  Usa cuando el usuario quiere escribir un paper, necesita estructura IMRaD, o solicita
  "escribir un documento de investigación".
language: es-CO
metadata:
  version: "1.0.0"
  trit: 0
  risk_tier: CAUTION
---

# Escritura Académica

## Propósito

Genera documentos académicos de alta calidad en formato APA 7 usando el lenguaje de composición Typst. Combina investigación, redacción y validación de citas en un flujo de trabajo integrado.

## Auto-Despliegue

Si los workflows de escritura académica no aparecen en los comandos del agente, ejecuta desde la raíz del skill:

```bash
python scripts/bootstrap_skill.py --workspace .
```

script: `bootstrap_skill.py` — detecta el agente y despliega los workflows automáticamente.

Esto detectará automáticamente el directorio de configuración del agente y desplegará los archivos necesarios.

**Requisito previo:** Verificar que Typst esté instalado en el entorno antes de generar documentos.

## Arquitectura

Este skill integra búsqueda, validación de citas y composición Typst. Cualquier cita rota o alucinada es un **error catastrófico**.

### Flujo de Trabajo

```
Usuario → Escritura Académica → Citas (scripts) → Typst
```

## Workflow Principal

### 1. Planificar

Definir alcance usando `references/imrad-guia.md`.

### 2. Redactar

Seguir estructura IMRaD según `references/imrad-guia.md`.

### 3. Citar

Usar scripts de búsqueda y validación para encontrar y verificar referencias:

- Buscar artículos: script: `search_google_scholar.py` o script: `search_pubmed.py`
- Extraer metadatos: script: `extract_metadata.py`
- Validar citas: script: `validate_citations.py`
- Convertir DOIs a BibTeX: script: `doi_to_bibtex.py`
- Formatear BibTeX: script: `format_bibtex.py`

### 4. Componer

Generar código Typst siguiendo `references/typst-scripting.md`.

### 5. Compilar

Producir PDF final con Typst.

## Validación de Citas (Crítico)

**Nunca** generar citas falsas o alucinadas. Antes de usar cualquier referencia:

1. Validar DOI con script: `validate_citations.py`
2. Verificar que la referencia existe realmente
3. Confirmar coincidencias de autor, año y título

## Referencias Rápidas

| Guía | Propósito |
| :--- | :--- |
| `references/imrad-guia.md` | Estructura IMRaD, estilo APA 7 |
| `references/diseno-investigacion.md` | Preguntas de investigación, ética |
| `references/publicacion-estrategia.md` | Selección de revista, peer review |
| `references/citation-buscar-pubmed.md` | Búsqueda en PubMed |
| `references/citation-buscar-scholar.md` | Búsqueda en Google Scholar |
| `references/citation-extraccion-meta.md` | Extracción de metadatos |
| `references/citation-validacion.md` | Validación de citas |
| `references/citation-formato-bibtex.md` | Formato BibTeX |
| `references/typst-scripting.md` | Sintaxis Typst, lógica, estado |
| `references/typst-calculo.md` | Modo matemático |
| `references/typst-graficos.md` | CeTZ,绘图, gráficos |
| `references/typst-paquetes.md` | Paquetes populares |
| `references/typst-layout.md` | Layout, páginas, grids |
| `references/typst-data.md` | Carga de datos (CSV, JSON) |
| `references/typst-bibliografia.md` | Bibliografía y cite() |

## Scripts Disponibles

| Script | Propósito |
| :--- | :--- |
| `scripts/bootstrap_skill.py` | Despliegue del skill |
| `scripts/search_google_scholar.py` | Buscar en Google Scholar |
| `scripts/search_pubmed.py` | Buscar en PubMed |
| `scripts/extract_metadata.py` | Extraer metadatos |
| `scripts/validate_citations.py` | Validar citas |
| `scripts/format_bibtex.py` | Formatear BibTeX |
| `scripts/doi_to_bibtex.py` | Convertir DOIs a BibTeX vía CrossRef |

## Verificación del Entorno Typst

Antes de compilar, verificar que Typst esté disponible:

```bash
typst --version
```

Si no está instalado, informar al usuario y ofrecer alternativas (LaTeX, Word).