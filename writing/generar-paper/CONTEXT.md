# Escritura Académica

Contexto del skill `escritura-academica`: generación de documentos académicos en español colombiano (es-CO) con formato APA 7 y validación estricta de citas para trabajos universitarios. El skill cubre todo el flujo: búsqueda de fuentes → extracción de metadatos → validación de citas → formateo BibTeX → composición Typst → compilación a PDF.

## Lenguaje

### Verificación de citas

**Validación por contenido (Tier C)**:
Verificación que abre el enlace del artículo citado, extrae título, autores y año de la fuente real, y los compara contra la entrada BibTeX usando coincidencia difusa para título y autores, y exacta para el año. Si el artículo no tiene DOI (fuente no formal), la verificación se limita a título de página y disponibilidad de URL.
_Evitar_: verificación superficial, validación solo de DOI

**Validación por resolución (Tier B)**:
Verificación que únicamente confirma que el DOI de la cita resuelve correctamente vía CrossRef, sin comparar el contenido de la entrada BibTeX contra los metadatos reales. Sirve como fallback cuando la verificación por contenido no es posible.
_Evitar_: validación completa

### Formato APA 7

**Formato estudiante**:
Configuración APA 7ª edición para trabajos universitarios. Incluye portada con título, nombre del autor, afiliación, curso, instructor y fecha de entrega. No lleva running head ni nota de autor.
_Evitar_: formato profesional, paper para revista

**Formato profesional**:
Configuración APA 7ª edición para publicación en revistas académicas. Incluye running head en cada página y nota de autor en la portada.
_Evitar_: formato estudiante, trabajo universitario

### Tipos de fuente

**Fuente formal**:
Publicación con identificador permanente (DOI): artículos de revista, papers de conferencia, capítulos de libro con ISBN. Admite verificación por contenido (Tier C).
_Evitar_: fuente verificable, publicación indexada

**Fuente no formal**:
Publicación sin DOI: página web, informe técnico institucional, documentación de software, repositorio de código, entrada de blog. Solo admite verificación de disponibilidad de URL y coincidencia de título.
_Evitar_: fuente informal, recurso web

### Herramientas externas

**EXA**:
API de búsqueda web semántica optimizada para agentes de IA. Se usa para descubrir artículos académicos mediante búsqueda por similitud semántica con categoría `research paper`. Requiere clave de API configurada en variable de entorno `EXA_API_KEY`.
_Evitar_: Google Scholar, buscador académico

**CrossRef**:
API de metadatos académicos. Provee datos estructurados (título, autores, año, revista) a partir de un DOI. Se usa tanto para extraer metadatos como para verificar citas por contenido.
_Evitar_: validador de DOI, extractor de metadatos

**Typst**:
Lenguaje de composición tipográfica markup-based. Alternativa moderna a LaTeX. El skill genera código Typst que se compila a PDF.
_Evitar_: LaTeX, procesador de texto

**versatile-apa**:
Paquete de Typst (template) que implementa el formato APA 7ª edición. Soporta español, formato estudiante y profesional, figuras, tablas, apéndices y bibliografía. Versión actual: 7.2.0.
_Evitar_: plantilla APA, tema APA

### Estructura del documento

**IMRaD**:
Estructura canónica de artículo académico: Introducción, Métodos, Resultados y Discusión. El skill guía al agente a seguir esta estructura para todo documento generado.
_Evitar_: estructura libre, ensayo

**BibTeX**:
Formato de archivo para almacenar referencias bibliográficas. Todos los scripts del pipeline de citas operan sobre archivos `.bib`.
_Evitar_: archivo de referencias, bibliografía

### Pipeline

**Pipeline de citas**:
Flujo completo de gestión de referencias: búsqueda (EXA) → extracción de metadatos (CrossRef/PubMed/arXiv) → validación (Tier C con fallback a Tier B) → formateo BibTeX → composición tipográfica en el documento.
_Evitar_: flujo de referencias, cadena de citas
