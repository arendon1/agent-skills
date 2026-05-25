# Validación de Citas

## Descripción

Verificar que todas las citas sean precisas, completas y resuelvan a publicaciones reales.

## Comandos de Validación

```bash
python scripts/citation-validar.py references.bib
python scripts/citation-validar.py references.bib --auto-fix --output fixed.bib
python scripts/citation-validar.py references.bib --report report.json --verbose
```

## Verificaciones

1. **Verificación de DOI**: Confirma que el DOI resuelve vía `doi.org`.
2. **Campos Requeridos**: Asegura que todos los campos obligatorios estén presentes.
3. **Consistencia de Datos**: Verifica años, formatos de páginas y nombres de autores.
4. **Detección de Duplicados**: Encuentra mismo papers citados con diferentes claves.
5. **Conformidad de Formato**: Verificación de sintaxis BibTeX.

## Errores Comunes

* **DOI Inválido**: El DOI no existe. (Acción: BUSCAR DOI correcto).
* **Campo Faltante**: Ej., falta `journal` o `year`. (Acción: Agregar info faltante).
* **Duplicado**: Dos entradas para el mismo paper. (Acción: Fusionar referencias).
* **Formato**: Errores de sintaxis que rompen la compilación. (Acción: Corregir corchetes/comas).

## Regla de Oro

**Validar temprano y frecuentemente**. Cualquier DOI que no resuelva es un ERROR CATASTRÓFICO.