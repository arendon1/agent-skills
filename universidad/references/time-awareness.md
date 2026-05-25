# Time Awareness

## Lógica de Detección de Periodo

El periodo se deriva automáticamente de las fechas de inicio de los cursos:

1. **Periodo (1 o 2)**:
   - Si mes de inicio ≤ 6 → Periodo 1
   - Si mes de inicio > 6 → Periodo 2

2. **Bloque (B1, B2, B3)**:
   - Bloque 1: Duración ≤ 6 semanas (42 días)
   - Bloque 2: Duración 7-12 semanas (43-84 días)
   - Bloque 3: Duración > 12 semanas (85+ días)

## Caché

- **Duración**: 7 semanas (49 días)
- **Validación**: `cache_valid_until = hoy + 7 semanas`
- **Refresco**: Si `hoy > cache_valid_until`, re-escanear workspace

## Ejemplo

```
Curso A: inicio 2026-01-26, fin 2026-03-08
Curso B: inicio 2026-03-10, fin 2026-04-28

Periodo: 2026-1 (mes 1 ≤ 6)
Bloque: B1 (42 días ≤ 42)
```