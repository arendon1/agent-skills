# Validación de Citas (Estructural)

## Descripción

Verifica la estructura y formato de las entradas BibTeX: campos requeridos,
formato de año, DOI, páginas, separadores de autores y detección de duplicados.

Para la verificación de contenido (comparar título, autores y año contra la fuente real),
consultar `references/citation-verificacion-contenido.md`.

## Comandos de Validación

```bash
# Validación estructural únicamente
python scripts/validate_citations.py references.bib

# Validación estructural + verificación de contenido (Tier C)
python scripts/validate_citations.py references.bib --check-dois

# Con reporte detallado
python scripts/validate_citations.py references.bib --check-dois --report reporte.json --verbose
```

## Verificaciones Estructurales

1. **Campos Requeridos**: Asegura que todos los campos obligatorios estén presentes según el tipo de entrada.
2. **Formato de Año**: Verifica que el año tenga 4 dígitos y esté en un rango razonable.
3. **Formato de DOI**: Confirma que el DOI tenga el formato `10.XXXX/...`.
4. **Rangos de Páginas**: Verifica que usen guion largo (`--`) en lugar de guion simple.
5. **Separadores de Autores**: Detecta uso de `;` o `&` en lugar de `and`.
6. **Detección de Duplicados**: Encuentra papers citados con diferentes claves, DOIs duplicados o títulos idénticos.

## Errores Comunes

* **Campo Faltante**: Falta `journal` o `year`. (Acción: Agregar información faltante).
* **DOI Inválido**: El DOI no tiene el formato correcto. (Acción: Corregir el DOI).
* **Duplicado**: Dos entradas para el mismo paper. (Acción: Fusionar referencias).
* **Formato de Autores**: Uso de `;` en lugar de `and`. (Acción: Reemplazar separadores).

## Regla de Oro

**Validar temprano y frecuentemente**. Ejecutar la validación estructural después de cada
modificación del archivo BibTeX, y la verificación de contenido (Tier C) antes de compilar.