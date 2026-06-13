# Actualización autónoma de cursos y gestión con ClickUp

El agente gestiona el ciclo de vida completo del curso: desde la extracción
inicial hasta las actualizaciones periódicas y el tracking de completación.
Las copias locales son insumos de trabajo; ClickUp es el sistema de registro
para el progreso del curso.

## Decisiones

### 1. Detección autónoma de cambios

El agente compara `Date.now()` contra el `timestamp` de `_cache/snapshot.json`
para determinar cuánto tiempo pasó desde la última sincronización. Si excede
un umbral (configurable, default 24h), lanza `cli_estado.py` automáticamente
al iniciar conversación sobre ese curso.

**Rechazado:** disparo manual vía CLI. Va contra la UX de conversación con
el agente y requiere que el usuario recuerde ejecutar el comando.

### 2. Snapshot como fuente de diff

`_cache/snapshot.json` indexa cada actividad por `url` de Moodle (inmutable)
y almacena `fecha_apertura`/`fecha_cierre` para `quiz` y `assign`. `page`,
`forum`, `resource` y `url` solo registran existencia. La comparación detecta:

- **Nueva**: URL presente en sidebar actual, ausente en snapshot
- **Fecha modificada**: URL existe en ambas, fechas difieren
- **Eliminada**: URL en snapshot, ausente en sidebar actual

**Rechazado:** comparar por nombre de actividad. Los nombres cambian,
las URLs de módulo Moodle son estables.

### 3. Extracción paralela por unidad

`cli_estado.py` lanza un subproceso por cada unidad del curso. Todos
comparten la misma instancia Chrome CDP (`--no-browser`). Esto reduce
el tiempo de escaneo de N×sequential a ~1×sequential.

Mismo patrón que `_init_parallel` para múltiples cursos.

### 4. ClickUp como sistema de registro

La lista de ClickUp del curso contiene una tarea por cada actividad del PGA.
El agente usa el skill `use-clickup` para:
- Crear la lista al inicializar el curso (`crear-lista`)
- Crear tareas con `due_date` por cada actividad (`crear-tarea`)
- Actualizar fechas cuando el diff de `estado` detecta cambios (`actualizar-tarea`)
- Marcar completadas las tareas a medida que el usuario avanza

Las copias locales en `[CÓDIGO]-nombre/` son insumos de trabajo: contienen
los materiales, instrucciones, y contexto necesario para completar cada
actividad. ClickUp refleja el estado de completación.

**Rechazado:** usar solo archivos locales para tracking. No hay visibilidad
de progreso entre sesiones, no hay recordatorios de fechas límite, y el
usuario tendría que revisar manualmente cada carpeta.

## Consecuencias

- `AGENTS.md` debe incluir `CLICKUP_LIST_ID` para que el agente sepa qué
  lista corresponde al curso.
- `cli_estado.py` debe ganar las capacidades de snapshot + diff + paralelismo.
- El agente debe tener acceso a `use-clickup` y al token `CLICKUP_API_KEY`.
- La snapshot solo se actualiza al finalizar un `estado` exitoso, no durante
  `init` (init la crea por primera vez).
