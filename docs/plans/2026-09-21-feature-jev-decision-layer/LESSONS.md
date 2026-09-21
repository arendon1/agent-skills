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

## Decisiones de diseño registradas

- **§12 se honra por subprocess, no por import**: el `jev_shim.py` de `gestionar-cursos`
  invoca el CLI de `jev-decision-layer` como subprocess. El `ai_score_jev.py` de
  `ai-check` hace sys.path a la utility porque ambos viven en el mismo repo, pero el
  contrato cross-skill sigue siendo el CLI.
- **El fallback es un modo de primera clase**, no una excepción: `mode="fallback"` con
  `uncertain=True` permite que todo consumidor degrade sin ramificar.
- **Los guardarraíles loguean, no bloquean**: la integración en `h5p_solve.py` añade
  entradas a `opportunities` y metadatos `jev_guard` al resultado; jamás altera el
  resultado primario ni aborta un run.
