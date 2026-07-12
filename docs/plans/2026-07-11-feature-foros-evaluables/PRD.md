# PRD: Foros evaluables → hilos principales de compañeros

## Goal

Extraer de cada foro evaluable (>0% en título) de un curso Moodle:
título+%, vencimiento, indicaciones, actividad, y los hilos principales
(root) de compañeros — solo el primer post, sin replies — para que el
usuario pueda escanear, resumir y decidir dónde participar.

## Why

Hoy `extractor_foro.py` filtra solo discusiones del profesor (uso intro:
Avisos, Consultas, Presentación). El usuario quiere el patrón opuesto
para foros de actividad: todos los hilos principales de cualquier autor,
con la descripción del foro como "qué hay que hacer", guardados en la
carpeta de la unidad correspondiente, no en `COMUNICACION/`.

## Scope

**Incluye:**
- Nuevo extractor `extraer_datos_foro(url, section_name)` que lee la
  página del foro y devuelve: `titulo`, `vencimiento`, `indicaciones`,
  `actividad`, `hilos` (lista con id, título, autor, fecha, último
  mensaje, réplicas, URL).
- Modificar `extraer_discusiones_foro`: quitar filtro de profesor,
  añadir cap de 20 hilos, usar cache por `discuss_id`.
- Función `extraer_primer_post_cached(discuss_id, url, cache)` que
  consulta/actualiza cache.
- Nueva cache `_cache/foros_cache.json` con `discuss_id` como key.
- Nuevo CLI `cli_foros.py`: `gestionar-cursos foros <CARPETA_CURSO>`.
- Output: `Unidad-X/Foros/<forum-slug>.md` — un archivo por foro, con
  metadata + todos los hilos inline (uno por `##` section).
- Hook en `cli_init.py` y `cli_estado.py` para correr el flujo de
  foros automáticamente durante init/sync.
- Detección de "es evaluable": regex `\((\d+)%\)` en el título. >0 →
  procesa; 0/no-match → skip.

**No incluye:**
- Reemplazo del flujo existente de foros introductorios (Avisos,
  Consultas, Presentación) en `COMUNICACION/`. Ese flujo sigue igual.
- Scraping de respuestas (replies). Solo el primer post de cada hilo.
- Resumen LLM de los hilos (queda como mejora futura).
- Tests automatizados E2E contra Moodle (manual: ejecutar contra un
  curso real y verificar).

## Acceptance

- [x] `uv run python cli_foros.py <CARPETA_CURSO>` procesa un curso y
  genera un `.md` por cada foro evaluable en `Unidad-X/Foros/`.
- [x] Foros sin porcentaje en el título se omiten (no se genera
  archivo).
- [x] Foros con `(0%)` o sin match se omiten.
- [x] Cada hilo extraído incluye: título, autor, fecha, último mensaje,
  réplicas, URL, contenido completo del primer post.
- [x] Cap de 20 hilos por foro (los hilos 21+ se omiten con warning).
- [x] Re-ejecución usa cache: hilos ya extraídos no se re-abren.
- [x] `cli_init.py` invoca el flujo de foros para actividades `forum`
  en unidades (no en intro/avisos).
- [x] `cli_estado.py` detecta hilos nuevos y los extrae; hilos
  removidos se marcan pero no borran el archivo local.
- [x] Foros introductorios (Avisos, Consultas, Presentación) siguen
  funcionando como antes.
- [x] `SKILL.md` documenta el nuevo comando y comportamiento.

## Verification

- Smoke tests unitarios: `test_extractor_foro.py` (4 tests, todos
  pasan) — `es_evaluable`, `_parsear_fecha_es`, `extraer_hilos_listado`,
  cap de 20.
- Test E2E simulado: `test_cli_foros_integration.py` valida el
  renderizado del markdown con HTML sintético basado en la captura del
  usuario. Pasan todos los asserts.
- Compilación: `python3 -m py_compile` en los 5 archivos modificados
  pasa tanto en el source (`agent-skills-v2/domain/`) como en el
  installed copy (`~/.agents/skills/`).
- Pendiente: test E2E contra un curso real de Uniremington. Eso
  requiere sesión activa en Moodle y la ejecuta Andrés manualmente
  tras deploy.

## Out of Scope (futuro)

- Cache invalidation por timestamp (hoy cache nunca expira, los hilos
  no cambian en Moodle).
- LLM summarization de cada hilo.
- Auto-detección de "a quién ya comenté" (requiere estado de Moodle
  sobre mis posts).
- Soporte de adjuntos en los hilos (imágenes, archivos).
