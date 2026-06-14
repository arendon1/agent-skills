# Verificación de Citas por Contenido (Tier C)

## Descripción

Verifica que cada cita en el archivo BibTeX corresponda exactamente al artículo
o fuente que dice citar, comparando título, año y autores contra los metadatos
reales de la fuente (CrossRef para DOIs, título de página para URLs). Esta
verificación va más allá de solo confirmar que el DOI resuelve.

## Niveles de Verificación

### Tier C — Comparación de Contenido (fuentes con DOI)

Aplica a: artículos de revista, papers de conferencia, capítulos de libro con DOI.

**Qué verifica:**

1. **DOI resuelve**: confirmar que el DOI dirige a una página real (HTTP < 400).
2. **Título coincide**: comparación difusa entre el título en BibTeX y el título
   en CrossRef. Umbral de similitud ≥ 0.85. Si cae por debajo, es **error crítico**.
3. **Año coincide**: comparación exacta entre el año en BibTeX y el año en CrossRef.
   Cualquier diferencia es **error crítico**.
4. **Primer autor coincide**: comparación difusa del apellido del primer autor.
   Umbral de similitud ≥ 0.75. Si cae por debajo, es **advertencia** (no bloquea).

**API utilizada**: CrossRef (`https://api.crossref.org/works/{doi}`)

### Tier B — Verificación de Disponibilidad (fuentes sin DOI)

Aplica a: páginas web, informes técnicos, documentación de software, repositorios.

**Qué verifica:**

1. **URL resuelve**: confirmar que la URL devuelve HTTP 200.
2. **Título de página coincide**: extraer `<title>` del HTML, limpiar sufijos
   comunes, y comparar difusamente contra el título en BibTeX. Si la similitud
   es < 0.85, es **advertencia** (requiere revisión manual).

**Nota:** Las fuentes sin DOI no pueden verificar autores ni año automáticamente.
Se recomienda revisión manual para estas fuentes.

## Comandos

```bash
# Validación completa con Tier C
python scripts/validate_citations.py references.bib --check-dois

# Solo validación estructural (sin verificación de contenido)
python scripts/validate_citations.py references.bib

# Con reporte detallado en JSON
python scripts/validate_citations.py references.bib --check-dois --report reporte.json --verbose
```

## Interpretación de Resultados

### Errores (debe corregir antes de compilar)

| Tipo | Significado | Acción |
|------|-------------|--------|
| `discrepancia_titulo` | El título no coincide con CrossRef | Buscar el DOI correcto o corregir el título |
| `discrepancia_year` | El año no coincide con CrossRef | Corregir el año en la entrada BibTeX |
| `doi_no_resuelve` | El DOI no existe o está roto | Buscar el DOI correcto o eliminar la cita |
| `url_no_resuelve` | La URL no está disponible | Buscar una URL alternativa o una fuente formal |

### Advertencias (revisar antes de compilar)

| Tipo | Significado | Acción |
|------|-------------|--------|
| `discrepancia_autor` | El primer autor no coincide | Verificar que el autor sea correcto |
| `discrepancia_titulo_url` | El título de la página difiere | Verificar manualmente que la fuente sea correcta |

## Regla de Oro

**Nunca incluir una cita sin verificar.** Cualquier discrepancia de título o año
es un error catastrófico que debe corregirse antes de compilar el documento.
Las advertencias de autor deben revisarse manualmente. Las fuentes sin DOI
siempre requieren revisión adicional porque la verificación automática es limitada.
