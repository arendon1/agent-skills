# Verificación de citas por contenido (Tier C) con fallback a resolución (Tier B)

El skill original solo verificaba que el DOI resolviera (Tier B), sin comparar los metadatos reales del artículo contra la entrada BibTeX. Se decidió exigir verificación por contenido (Tier C) como estándar: abrir la fuente, extraer título, autores y año, y compararlos contra la cita. Si la fuente no tiene DOI (fuente no formal), se aplica fallback a verificación de URL y título de página (Tier B).

## Opciones consideradas

1. **Solo Tier B (DOI resuelve)** — rechazada porque permite fabricar citas con DOI real de otro artículo, sin que el validador detecte la discrepancia.
2. **Tier C con fallback a Tier B** — elegida. Da prioridad a la verificación completa, pero no bloquea fuentes legítimas sin DOI.
3. **Tier C sin fallback** — rechazada por excesivamente restrictiva: las fuentes no formales (sitios web, informes técnicos, documentación) quedarían sin validar o bloqueadas.

## Consecuencias

- `validate_citations.py` debe implementar comparación difusa de título (umbral ≥ 0.85), exacta de año y parcial de autores.
- Para fuentes con DOI, CrossRef es la API de verificación. Para fuentes sin DOI, se verifica disponibilidad de URL (HTTP 200) y coincidencia del título de página.
- Las discrepancias se reportan como error crítico (título/año) o advertencia (autores), nunca se corrigen automáticamente.
