# Foros evaluables — referencia

Detalle de `gestionar-cursos foros` y la lógica de extracción. El
SKILL.md principal contiene la descripción de uso; este archivo tiene
los detalles de implementación, output, y casos edge.

## Detección de "evaluable"

```python
es_evaluable(titulo) → (bool, int)
# regex: r"\((\d+)%\)"
# (6%)  → (True, 6)
# (0%)  → (False, 0)
# (no match) → (False, 0)
```

La detección se hace por el título del foro en la sidebar. Si el
profesor no incluye `(X%)` en el título, el foro se omite aunque
tenga calificación real en Moodle.

## Selectores HTML (Moodle moderno)

| Elemento | Selector |
|---|---|
| Título | `h1` o `.page-header-headings h1` |
| Vencimiento | `div[data-region="activity-dates"]` con `<strong>Vencimiento:</strong>` |
| Indicaciones | Bloque que contiene "Para participar siga las instrucciones" |
| Actividad | Bloque que contiene "Pregunta orientadora" |
| Hilos | `table.forumheaderlist tr` o `[data-region="discussion-list"] tr` |
| Discuss ID | regex `discuss\.php\?d=(\d+)` sobre `href` del título del hilo |

## Cache

Archivo: `<curso>/_cache/foros_cache.json`

Estructura por `discuss_id`:

```json
{
  "140651": {
    "titulo": "Amenazas de Seguridad",
    "autor": "Juan Fernando Quintero",
    "fecha": "7 jul 2026",
    "url": "https://aulavirtual.uniremington.edu.co/mod/forum/discuss.php?d=140651",
    "contenido": "[texto completo del primer post]",
    "extraido_en": "2026-07-11T19:00:00"
  }
}
```

**Política:** los hilos no cambian (a diferencia de las fechas de
actividades), así que el cache nunca expira por timestamp. Si un hilo
se borró en Moodle, queda en el cache y se reporta como "removido" en
el próximo `estado` (no se borra el archivo local automáticamente).

## Cap de 20 hilos

`MAX_HILOS = 20` en `extractor_foro_evaluable.py`. Si el foro tiene
más de 20 hilos visibles, se procesan los primeros 20 y se omite el
resto. Configurar modificando la constante.

## Hooks

- `cli_init.py` línea ~290 (`elif tipo == "forum":`): si el foro es
  evaluable, llama a `_procesar_foro_evaluable.procesar_foro_en_unidad`
  en lugar del flujo viejo. Si NO es evaluable, sigue yendo por el
  flujo viejo (intro/Avisos → `COMUNICACION/`).
- `cli_estado.py` final del flujo: nueva función
  `revisar_hilos_foros_evaluables` que para cada foro evaluable en
  unidad compara hilos actuales vs cache y reporta nuevos/removidos.

## Estructura de output

```
Unidad-1/
└── Foros/
    └── Foro_1_Seguridad_en_aplicaciones_web_6.md
```

Slug del foro: `_slug_foro()` quita `(X%)`, caracteres no-`\w`, y
colapsa espacios en underscores. Truncado a 80 chars.

Si el foro está en una sección que no es `Unidad X` (ej: General,
Introducción), va a `General/Foros/`. Esto NO debería pasar en la
práctica porque el filtro por sección se aplica en `cli_foros.py` y
en el hook de `cli_init.py`.

## Casos edge

- **Foro sin tabla de hilos:** el parser devuelve `hilos=[]`. Se
  genera el markdown con metadata + 0 hilos.
- **Foro con Hilos pero sin caja de "Para participar...":** las
  indicaciones quedan como "[Sin indicaciones]". Mismo patrón para
  actividad.
- **Vencimiento en formato distinto:** el parser de fecha usa regex
  con días en español; si Moodle usa otro formato (raro), devuelve el
  string crudo y se ve feo en el markdown.
- **Más de 20 hilos:** ver cap arriba. Para modificar el cap, cambiar
  `MAX_HILOS` en el módulo.
- **Foro con `Unidad` en el nombre pero NO como sección:** el match
  de sección es por el nombre de la SECCIÓN del sidebar, no del foro.
  Si el sidebar dice "Unidad 1" pero el foro se llama "Foro X (5%)"
  sin "Unidad" en el nombre, sigue funcionando — el filtro de
  evaluable es por el título del foro.
