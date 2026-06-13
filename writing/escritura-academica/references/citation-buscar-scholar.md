# Búsqueda en Google Scholar

## Descripción

Google Scholar proporciona la cobertura más completa entre disciplinas.

## Búsqueda Básica

```bash
python scripts/citation-buscar-scholar.py "CRISPR gene editing" \
  --limit 50 \
  --output results.json
```

## Estrategias Avanzadas

* **Frases exactas**: Usar comillas: `"deep learning"`
* **Búsqueda por autor**: `author:LeCun`
* **Búsqueda por título**: `intitle:"neural networks"`
* **Exclusiones**: Usar `-`: `machine learning -survey`
* **Sitio específico**: `site:arXiv.org`, `source:Nature`
* **Rangos de fecha**: Usar `2020..2024` en la consulta.

## Mejores Prácticas

1. **Encontrar Papers Seminales**:
   * Ordenar por conteo de citas (más citados primero).
   * Ver "Citado por" para evaluar impacto.
2. **Usar términos específicos**: Incluir términos técnicos y acrónimos.
3. **Trabajo reciente**: Filtrar por años recientes en campos de rápido movimiento.
4. **Revisiones**: Buscar `intitle:review` para obtener panoramas.