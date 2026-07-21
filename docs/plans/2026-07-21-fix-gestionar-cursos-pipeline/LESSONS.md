# LESSONS — fix(gestionar-cursos)

## L1 — El bug de `float("-" or 0)` es una trampa clasica de Python

- **Sintoma:** `ValueError: could not convert string to float: '-'`
- **Causa:** `valor or 0` solo captura `valor == ""` o `valor is None`.
  Cualquier string no vacio (incluido `"-"`, `"N/A"`, `"—"`) es truthy.
- **Aprendizaje:** `or 0` NO es defensivo para "cualquier string no
  parseable". Hay que enumerar centinelas explicitos.
- **Portable:** preferir `_parse_porcentaje()` con lista explicita de
  centinelas, sobre una expresion inline.

## L2 — Las dependencias "imaginarias" son un olor a codigo

- **Sintoma:** `NameError: name 'get_client' is not defined` al primer uso.
- **Causa:** el script llamaba funciones de `use-clickup` sin importarlas.
  El comentario "delegated to the agent" ocultaba la deuda.
- **Aprendizaje:** un script estructurado como ejecutable end-to-end DEBE
  ser ejecutable end-to-end. Si no, el comentario miente.
- **Portable:** o se implementa el wiring completo, o se elimina la opcion
  `--apply` y se documenta el script como "solo previsualizacion".

## L3 — El orden de operaciones en main() importa cuando hay un paso cosmetico

- **Sintoma:** `_imprimir_resumen` crasheaba antes de `_actualizar_md_actividad`
  y `_actualizar_snapshot`, perdiendo el trabajo de extraccion.
- **Causa:** orden collect → persist → format(report) → persist2; la segunda
  persistencia se saltaba si format revienta.
- **Aprendizaje:** persistir primero, formatear despues. El formato es para
  el humano; los datos en disco son para el sistema.
- **Portable:** orden canonico collect → persist → format → report.

## L4 — Buscar antes de asumir

- **Contexto:** la leccion "status_id vs status name" ya existia documentada
  en `sync_calificaciones_clickup.py:24-28`. Al implementar el fix B4, la
  respuesta estaba literalmente en el archivo de la skill vecina.
- **Aprendizaje:** antes de implementar un fix, buscar en el repo si ya hay
  nota sobre el bug. `grep -r "leccion\|lesson\|LPA\|gotcha" --include="*.md"`.

## L5 — El gradebook HTML crudo (295 KB) se queda en disco aunque el script falle

- **Contexto:** `_descargar_gradebook` escribe el HTML ANTES de parsear. Si
  el parser falla, el HTML queda huerfano en `_cache/`.
- **Decision:** NO incluido en este fix (cambio de scope). Documentar como
  known-issue. Plan aparte si vale la pena.

## L6 — El test minimo viable protege contra regresiones futuras

- **Aprendizaje:** el costo de anadir el test minimo (3 funciones, ~20
  lineas) es despreciable comparado con el costo de diagnosticar el bug
  en produccion. Anadir tests con cada fix, no como tarea aparte.

## L7 — El agente es el verdadero orquestador — pero solo si tiene las primitivas

- **Aprendizaje:** "delegar al agente" funciona si el agente tiene las
  primitivas disponibles. Hoy el skill `use-clickup` SI las tiene. El
  problema era que `cli_clickup.py` no las exponia.

## L8 — Las caches locales pueden estar stale

- **Sintoma:** un skill que depende de archivos locales (`snapshot.json`,
  `calificaciones.json`, `clickup.json`) puede estar leyendo informacion
  de hace horas o dias. El delta que produce contra ClickUp puede estar
  basado en realidad obsoleta.
- **Causa:** no hay timestamp de "ultima sincronizacion fresca" en los
  artefactos locales. El script no sabe cuando fue la ultima vez que se
  leyo Moodle realmente.
- **Aprendizaje:** los scripts de gestion de estado deben REPORTAR la
  antiguedad de su input (`_meta.source_fetched_at`, `_meta.stale`),
  no solo procesarlo. El agente decide cuando re-sincronizar; el script
  solo informa.
- **Portable:** todo artefacto con `_meta.generated_at` debe acompanarse
  de `_meta.source_freshness` o un threshold de "stale" configurable.
  Tests E2E deben incluir el caso "cache de 48h + 1 cambio en Moodle".

## L9 — La regla de no-import entre skills de dominio

- **Contexto:** `gestionar-cursos` necesita `use-clickup` para sincronizar
  tareas. La primera lectura fue "importar get_client" — pero esa lectura
  viola el principio de composicion: cada skill debe ser desplegable
  independientemente, sin requerir que otro skill este instalado en el
  mismo path.
- **Causa:** la tentacion de "reusar" el cliente HTTP ya construido en
  lugar de producir un artefacto que el agente aplique con la herramienta
  adecuada.
- **Aprendizaje:** el hecho de que un skill USE a otro no significa que
  deba importarlo. `use-clickup` es una API que el agente invoca, no una
  libreria que el skill linkea. El contrato entre skills es el artefacto
  JSON que el primero produce y el segundo (vía agente) consume.
- **Portable:** cuando un skill A necesita capacidades de un skill B, el
  patron es: A produce un artefacto declarativo (JSON, YAML) que describe
  lo que quiere hacer; el agente lee el artefacto y usa B para aplicarlo.
  A nunca importa B. B nunca sabe que A existe.
- **Anti-patron opuesto:** "skill A es util sin skill B" — cierto, pero
  "skill A requiere skill B en su path de import" rompe deployabilidad
  independiente. Test: `cd /path/to/A && uv run python A/script.py`
  sin B presente debe fallar LIMPIO (mensaje claro), no con
  `ModuleNotFoundError` en runtime.

## L10 — ClickUp es terminal, no se reorganiza desde codigo

- **Contexto:** el plan original propuso "delete + create" para actividades
  que cambian de nombre o tipo entre Moodle y ClickUp. El usuario corrigio:
  ClickUp es donde el humano organiza su trabajo, no un estado que el
  script puede reorganizar arbitrariamente.
- **Causa:** tentacion de "limpiar" el workspace de ClickUp cuando Moodle
  refleja un cambio. Asume que ClickUp es otra base de datos mas.
- **Aprendizaje:** ClickUp es terminal en el flujo. Cambios en Moodle
  producen `to_update` (PUT con diff) o `to_archive` (status cancelled,
  NUNCA DELETE). Renombres, reclasificaciones, merges, splits son
  decisiones del humano en su workspace.
- **Portable:** en general, todo sistema donde el humano es el owner
  final del estado debe recibir `to_update` / `to_archive`, no
  `to_delete + to_create`. El historial del humano es sagrado.
- **Implicacion de diseno:** el `sync_plan.json` schema incluye
  `to_archive` con campo `reason` (string libre: "removed_from_moodle",
  "renamed_in_moodle", "superseded") para que el humano pueda auditar
  por que una tarea quedo en estado cancelled.

## L11 — Maxima autonomia del agente, pausa solo para input destructivo

- **Regla del usuario (2026-07-21):** "este skill ha de permitir a los agentes
  maxima autonomia cuando el usuario les ha dado alguna instruccion. El
  objetivo siempre es cumplir con minima ineraccion humana, a menos de que
  una situacion critica lo amerite, como algun tipo de accion destructiva."

- **Causa de la regla:** el humano es el cuello de botella. Cada vez que
  el agente pausa para pedir confirmacion, se pierde el valor principal
  de automatizar. Los agentes tienen capacidad de leer contexto, hacer
  pre-checks, y detectar ambiguedad no determinista — usenla antes de
  preguntar.

- **Implicacion de diseno #1:** el `sync_plan.json` lleva `_meta.orchestration_hint`
  con `order`, `tools_required` y `pause_for_human`. El agente no tiene
  que adivinar la secuencia ni las capabilities — las lee del plan.

- **Implicacion de diseno #2:** `references/sync-flow.md` es un **playbook
  ejecutable** (pasos numerados, no documentacion descriptiva). El agente
  lo lee una vez, ejecuta, reporta. NO improvisa.

- **Implicacion de diseno #3:** `references/sync-flow.md` §C declara
  acciones destructivas PROHIBIDAS. El agente aborta ESA operacion si
  cae en §C, no consulta al humano. La prohibicion ya esta en el playbook.

- **Implicacion de diseno #4:** SKILL.md declara explicitamente
  `Modo de operacion: autonomo por defecto` para que el primer read del
  agente no genere la pregunta "¿le pregunto al humano?".

- **Portable:** todo skill que produce artefactos para un agente deberia
  declarar su modo de operacion (autonomo / colaborativo / manual) en
  el frontmatter o en una seccion visible del SKILL.md. La ambiguedad
  sobre "¿puedo ejecutar sin pedir?" es la principal causa de friccion
  innecesaria.

- **Excepciones que SI justifican pausa humana:**
  - Operacion destructiva no listada en §C (DELETE no planificado,
    modificacion de status personalizado, etc.).
  - Conflicto de carrera donde el estado real diverge del `diff.from`
    y la decision de como resolver no es determinista.
  - `unresolved` con razon no determinista (listadas en §B de sync-flow.md).
  - Falta de capability requerida (`tools_required` del plan).
