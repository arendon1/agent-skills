# LESSONS — jev-decision-layer integration

## Bugs encontrados durante la implementación (pagar y no repetir)

### L1 — Tuple-sugar ambigua para `score` en el cliente JEV
`_normalize_one(key, type_, instr, opts, rng)` recibía `("score", "rate", 5)` y mapeaba
`5` al slot `opts` (que para `choice` son las opciones), dejando `rng=None` → "range_max
required". **Invariante**: en el tuple-sugar, la 3ª posición es polimórfica por tipo —
`choice`→opciones, `score`→`range_max`, `noul`→ignorada. El parser debe resolver el slot
según `type_`, no asumir un solo significado.

### L2 — JSON no tiene tuples (stdin del CLI)
El CLI acepta la forma sugar `{key: (type, instr)}`, pero un payload enviado por stdin
llega con listas JSON, no tuples. `isinstance(v, tuple)` fallaba. **Invariante**: toda
frontera JSON debe normalizar `list→tuple` antes de entrar al parser de sugar.

### L3 — `strict=True` no elevaba cuando la autodetección caía a fallback
El chequeo de credenciales faltantes vivía en la rama "modo explícito", pero
`JEV(strict=True)` sin env resolvía `chosen="fallback"` por `_auto_detect` y esquivaba
la validación. **Invariante**: un modo "estricto" debe fallar en TODAS las rutas que
llegan a fallback, incluida la autodetección, no solo el override explícito.

### L4 — Fixtures de pytest no cruzan a subprocess
`run_cli()` lanza un subprocess que escribe al `cost-log.jsonl` real; el fixture
`clean_env` solo parcheaba el proceso del test. El assert `calls == 0` veía 6.
**Invariante**: si un test spawnea un subprocess, la limpieza de estado compartido debe
ser `autouse` en el archivo Y limpiar el path real, no solo el mockeado.

### L5 — SKILL.md > 500 líneas por 15 líneas de contenido nuevo
`ai-check` ya estaba en 505 líneas; cualquier adición viola §15. La solución no es
recortar prosa valiosa: es extraer secciones de referencia a `references/*.md` y dejar
un puntero. Dos extracciones (jev-integration.md, detector-landscape.md) dejaron el
SKILL en 499.

## Lecciones del review (Planner→Reviewer)

### L6 — "Verificado exhaustivamente" puede ser falso y envenena todo el plan
El Planner afirmó con seguridad que una extensión no existía ("grep exhaustivo"); el
Reviewer la encontró cargada en `settings.json` + `pi-extensions/`. **Invariante**: una
afirmación de ausencia (\"X no existe\") exige evidencia positiva (el grep con su salida),
no una conjunción de negaciones. Y en un plan, una verificación falsa degrada la
confianza en todas las demás.

### L7 — Un guard-rail de vendor sin segunda implementación no bloquea nada
El seam `JevProvider` para Laya es una promesa hasta que exista la segunda implementación.
**Invariante**: un "anti-lock-in seam" solo cuenta si al menos un segundo backend está
implementado (aunque sea un stub que pasa el contrato de la interfaz).

### L8 — El egreso es parte del diseño, no un detalle de implementación
El plan diseñó rutas HTTP a hosts nuevos sin la compuerta de announce-then-run exigida
por las directivas de seguridad de la máquina. **Invariante**: todo plan que añade un
host de salida debe incluir la decisión de autorización en su lista de "decisiones
humanas", con el mismo peso que las decisiones de arquitectura.

### L9 — Una variable de entorno ambiente se coló en los tests (y los hizo lentos, no rojos)
Al añadir el backend `openrouter` con auto-detección, 8 tests que esperaban `mode="fallback"`
comenzaron a elegir `openrouter` — porque `OPENROUTER_API_KEY` está configurada de verdad en
esta máquina. El fixture limpiaba `JEV_/TYPESAFE_/VERCEL_/AI_GATEWAY_/LAYA_` pero no
`OPENROUTER_`. Síntoma revelador: la suite pasó de 1.3s a **111s** (llamadas de red reales),
no a rojo inmediato. **Invariante**: al ampliar la superficie de auto-detección, hay que
ampliar la lista de prefijos que el fixture neutraliza en el MISMO commit. Y un salto de
runtime de dos órdenes es señal de red, no de lógica.

### L10 — El costo publicitado se mide contra el baseline equivocado
TypeSafe anuncia "40-400x más barato". Medido contra modelos frontera (GPT-5.6 Sol a
$0.084/caso), es cierto. Medido contra nuestro propio carril barato (`v4-text`), JEV es
**1.6x** — y a nuestro tamaño real de estado la diferencia absoluta es $0.00001/llamada
(18 centavos al mes). **Invariante**: un multiplicador de costo sin baseline declarado no
es un dato; es marketing. Siempre recalcular contra el carril que realmente se usaría.

### L11 — El razonamiento de un LLM es el costo oculto del camino estructurado
En el backend OpenRouter, el mismo prompt con `response_format: json_schema` tardó 5.9s con
108 tokens de salida por defecto, y **1.6s con 11 tokens** al apagar el razonamiento
(`reasoning: {"enabled": false}`). Un clasificador no necesita cadena de pensamiento; el
pensamiento era el 90% de la latencia y del gasto. **Invariante**: cuando el output está
restringido a un esquema, apagar el razonamiento es la optimización de mayor rendimiento.

### L12 — El shim devolvía un dataclass; el llamador usaba `.get()`
La integración del guardarraíl de slides hacía `guard.get("uncertain")` sobre un
`GuardVerdict`, que es un dataclass: `AttributeError`. Estaba dentro de un
`try/except` que solo anotaba `jev_guard_exception`, así que **el guardarraíl nunca
registró un veredicto y nada falló visiblemente**. **Invariante**: cuando el
consumidor de una API nueva vive dentro de un `try/except` que degrada, agregar un
test que compruebe que la ruta DE ÉXITO se ejecutó — no basta con que no crashee.

### L13 — El wrapper anidaba las respuestas y el parser las esperaba planas
`laya_server.py` devolvía `{"answers": {...}}`; `_parse_response` buscaba las claves
al nivel raíz (forma de TypeSafe). Resultado: **toda decisión vía Laya leía 0.0** —
un falso negativo silencioso en cada guardarraíl. Lo cazó el test end-to-end real,
no los unitarios (que usaban la forma plana porque yo la asumí). **Invariante**: un
parser entre dos implementaciones propias debe testearse contra LA SALIDA REAL de
la otra, no contra la forma que uno recuerda. Y aceptar ambas formas cuando el
contrato no está fijado.

### L14 — Un edit atómico que falla no deja NADA aplicado
Un lote de 4 edits falló en el índice 3; los tres anteriores tampoco se aplicaron.
Yo asumí que sí, y construí encima: la firma de `_drag_ftw` quedó vieja mientras el
call site ya pasaba los argumentos nuevos → `TypeError` esperando en runtime.
**Invariante**: tras un lote de edits que reporta fallo, verificar el estado REAL
del archivo (grep de la firma, del cuerpo) antes de seguir construyendo.

### L15 — El umbral de confianza es propiedad del backend, no del preset
El mismo estado de slide dio `score_at_max` = 0.81 con Laya y ~0.99 (reportado) con
JEV. Con un umbral fijo de 0.95, Laya producía **falso negativo en un slide
correcto**. **Invariante**: cuando dos implementaciones del mismo contrato devuelven
probabilidades, sus ESCALAS no son comparables sin verificación. El umbral va en la
config por backend, y el veredicto `uncertain` cubre el caso "no hay umbral para
este backend".

### L16 — Un modelo de decisión NO es un juez general; es un motor de verificación de estado
El preset `ai_dimensions_v1` (juicio estilístico: "¿este texto abusa de em-dashes?")
aplicado a Laya dio el resultado **INVERTIDO**: slop = 32/100 "likely_human", prosa
humana real = 62/100 "likely_ai". En cambio `slide_done_v1` (verificación de estado:
"¿este slide llegó al máximo puntaje?") dio 6/7 correcto. La base de Laya es
ModernBERT, entrenada con RLCD sobre tareas de decisión — no sobre estética.

**Invariante**: antes de prometer un preset contra un backend nuevo, verificar que
la pregunta caiga dentro de su distribución de entrenamiento. Las preguntas de
**propiedad concreta y comprobable** (tipo NLI) funcionan; las de **juicio
subjetivo** no. Un preset diseñado para un modelo imaginario no transfiere.

### L17 — La serialización del estado es la mayor palanca de calidad
El caso "Blanks completo" dio 0.210 (rechazo, falso negativo) con un texto que
decía "feedback reports 4 of 4 correct". Al añadir las señales explícitas
("every question has been answered and the slide is complete", "the maximum"),
subió a **0.737** y pasó. **Invariante**: el guardarraíl vale lo que vale la
descripción del estado. Serializar los CUES que el modelo necesita (exhaustividad,
progreso, máximo alcanzado) no es cosmética — es la diferencia entre 0.21 y 0.74.

## Decisiones de diseño registradas

- **El backend por defecto es el host ya autorizado.** El orden de auto-detección pone
  OpenRouter antes que Vercel/TypeSafe a propósito: consolidar egreso es una propiedad de
  seguridad, no una preferencia. Un host nuevo solo entra con key explícita.
- **`reasoning: off` es default en la ruta OpenRouter**, con `JEV_OPENROUTER_REASONING=1`
  para revertir cuando la calidad importe más que la latencia.
- **Laya es el backend por defecto para los guardarraíles.** Medido contra
  OpenRouter sobre los mismos 7 casos: 6/7 vs 5/7, 712ms vs 14173ms, $0 vs
  $0.000124. Y su error fue un rechazo seguro, mientras el de OpenRouter fue un
  **falso positivo** — la dirección peligrosa para un guardarraíl.
- **Los ejemplos viven en `examples/`** (`slide_guardrail_demo.py` es el que
  funciona; `ai_check_demo.py` documenta el caso que NO funciona con Laya).
- **`decide` es el verbo de los guardarraíles, no `classify`.** `decide` aplica la
  regla del preset con el umbral del backend que sirvió la llamada, y devuelve
  `pass`/`fail`/`uncertain`. `classify` solo devuelve números crudos.
- **Laya se consume como servicio efímero, no como daemon.** El patrón
  arranca-corro-mato vive en `laya_on_demand.py` y respeta la directiva de
  listeners locales y procesos que mueren.
- **§12 se honra por subprocess, no por import**: el `jev_shim.py` de `gestionar-cursos`
  invoca el CLI de `jev-decision-layer` como subprocess. El `ai_score_jev.py` de
  `ai-check` hace sys.path a la utility porque ambos viven en el mismo repo, pero el
  contrato cross-skill sigue siendo el CLI.
- **El fallback es un modo de primera clase**, no una excepción: `mode="fallback"` con
  `uncertain=True` permite que todo consumidor degrade sin ramificar.
- **Los guardarraíles loguean, no bloquean**: la integración en `h5p_solve.py` añade
  entradas a `opportunities` y metadatos `jev_guard` al resultado; jamás altera el
  resultado primario ni aborta un run.
