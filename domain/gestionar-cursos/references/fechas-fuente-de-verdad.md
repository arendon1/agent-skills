# Fechas — fuente de verdad

**Regla de oro: la fuente de verdad operativa de las fechas de
entrega NO es el PGA (tabla DO-FR-66 del Microcurrículo), sino las
fechas de apertura y cierre configuradas por el profesor en cada
actividad de Moodle.**

## Formato canonico

Todas las fechas se normalizan a **ISO 8601** (`YYYY-MM-DD`).

En archivos markdown se muestra dual:

```markdown
| Actividad | Fecha Inicio | Fecha Fin |
|-----------|--------------|-----------|
| Prueba Inicial | 26/1/2026 (2026-01-26) | 1/2/2026 (2026-02-01) |
```

La columna con formato local aparece siempre junto a la ISO para
mantener legibilidad humana sin perder la maquina-leibilidad.

El PGA es un documento pedagógico de planeación. Una vez el curso
está vivo, el profesor ajusta fechas directamente en Moodle (extiende
plazos, cambia aperturas, reorganiza unidades). Si se confía
ciegamente en el PGA para sincronizar ClickUp, se sobreescriben las
fechas reales con las planeadas.

## Dónde vive la fecha real en Moodle moderno

```html
<div data-region="activity-dates" class="activity-dates">
  <div><strong>Abrió:</strong> lunes, 6 de julio de 2026, 00:00</div>
  <div><strong>Cierra:</strong> domingo, 16 de agosto de 2026, 23:59</div>
</div>
```

Para foros la etiqueta es **`<strong>Vencimiento:</strong>`** (una
sola fecha). El extractor debe leer
`div[data-region='activity-dates']` (NO tablas `.quizinfo`/`.assigninfo`,
que son legacy) y convertir fechas en castellano
("lunes, 6 de julio de 2026, 00:00") a ISO 8601.

### Variantes de etiqueta según el estado de la actividad

Moodle cambia la etiqueta de la `<div>` de cierre según el momento:

| Estado de la actividad | Etiqueta HTML | Ejemplo |
|---|---|---|
| Aún no ha abierto | `Apertura:` / `Abre:` | `<strong>Apertura:</strong> lunes, 6 de julio de 2026, 00:00` |
| Abierta actualmente | `Cierra:` | `<strong>Cierra:</strong> domingo, 12 de julio de 2026, 23:59` |
| **Ya cerrada (pasado)** | **`Cerró:`** | `<strong>Cerró:</strong> domingo, 12 de julio de 2026, 23:59` |

**Bug histórico (2026-2-B1):** la primera versión del extractor solo
reconocía `Cierra:` / `Cierre` y NO `Cerró:`. Al re-ejecutar `estado`
después de que las actividades de la semana 1 ya habían cerrado
(2026-07-12 23:59), la snapshot nueva perdía las fechas de Prueba
Inicial y Lección 1. El extractor ahora reconoce ambas formas
(`Cierra:` y `Cerró:`) en `_LABELS_CIERRE` y siempre debe re-extraer
fechas para TODAS las actividades evaluables, sin importar si
están abiertas o cerradas.

Para workshops hay 4 etiquetas en secuencia y la **última gana**:
`Envíos abiertos` → `Cierre de envíos` → `Apertura de evaluaciones` →
`Cierre de evaluaciones`. La snapshot termina guardando la fase de
**evaluación** (`Apertura de evaluaciones` → `Cierre de evaluaciones`),
que es la ventana donde el estudiante debe evaluar a sus pares.

## Flujo correcto de sincronización de fechas

1. El PGA se extrae en `init` como **referencias** de planeación.
2. `estado` extrae las fechas reales de Moodle y las guarda en
   `_cache/snapshot.json` (`fecha_apertura`/`fecha_cierre` por
   actividad).
3. La sincronización con ClickUp (`cli_clickup.py`) **debe preferir
   `snapshot.json` sobre `PGA.md`**. Si una actividad existe en la
   snapshot con fechas no vacías, esas son las autoritativas;
   `PGA.md` solo se usa como respaldo para actividades no
   visitables (páginas, URLs).
4. Tras sincronizar, **actualizar `PGA.md`** para que refleje las
   fechas reales y futuras re-sincronizaciones no reviertan el cambio.

## Lección dura (2026-2-B1)

El primer `cli_clickup.py` usaba `PGA fecha_fin` como única fuente.
Las fechas reales de LPA1 divergieron del PGA (profesor extendió
Examen 02 hasta +42 días, abrió Tarea 04 dos semanas antes). Una
re-ejecución de `clickup-sync` habría revertido todas las
correcciones manuales. Usa siempre la snapshot de Moodle como
autoridad.

## Conversión de zona horaria para ClickUp

Las fechas de Moodle están en hora de Colombia (America/Bogota,
UTC-5 fijo, sin DST). Al convertir a epoch ms para la API de
ClickUp, usar `datetime.fromisoformat(s)` con `tzinfo=` explícito
UTC-5 — NO `iso_to_milliseconds` de `use-clickup` (anteriormente
truncaba el componente horario vía `strptime(iso[:10])`; ahora
arreglado).

Adicionalmente, forzar siempre `start_date_time=true` y
`due_date_time=true` en el payload; si se omite, ClickUp
re-normaliza la fecha a su propio huso y desplaza el epoch.
