---
name: gestionar-cursos
description: >-
  Extrae información de cursos Moodle Uniremington y organiza estructura
  de carpetas local. Usa cuando necesites inicializar cursos, sincronizar
  contenido o verificar estado de un curso vs Moodle.
invocation: user
layer: domain
loop: gestionar-cursos
provides: [moodle-course-management]
deliverable: organized local course structure synced with Moodle + ClickUp tasks
language: es-CO
---

# gestionar-cursos

Herramienta autónoma para gestión de cursos universitarios en la plataforma
Moodle de Uniremington (aulavirtual.uniremington.edu.co).

## Autenticación

Antes de cualquier navegación:

1. Navegar a `https://aulavirtual.uniremington.edu.co/my/`
2. Verificar estado:
   - **NO AUTENTICADO**: URL contiene `login/index.php` o texto "Usted no se ha identificado"
     → Detener y pedir al usuario: "Por favor inicia sesión en Moodle manualmente"
   - **AUTENTICADO**: Ver nombre "Andres Felipe Rendon Hernandez" o encabezado "Área personal"
     → Continuar

## Detección de Plataforma

El skill detecta automáticamente qué herramienta de navegación está disponible:

1. **browser_tool** → navegación integrada (sin interfaz gráfica)
2. **open_browser** → ventana externa del SO (navegador del sistema)
3. **selenium** → Terminal / CLI (Chrome DevTools Protocol)
4. **Ninguna** → Error con instrucciones de instalación

### Terminal / CLI — Alternativa

Cuando se ejecuta desde terminal (sin agente IDE):

- Se conecta a Chrome vía **CDP** (`localhost:9222`)
- Si Chrome no está abierto con `--remote-debugging-port=9222`, se lanza automáticamente una instancia visible
- El usuario inicia sesión en Moodle en esa ventana
- El script espera y continúa la extracción automáticamente

**Requisitos:**
```bash
pip install selenium beautifulsoup4 lxml requests
```

**Uso desde terminal:**
```bash
cd gestionar-cursos/scripts
uv run python cli_init.py "https://aulavirtual.uniremington.edu.co/course/view.php?id=10272" \
  --destino "C:/Users/.../Universidad/2026-2-B1"
```

El período y bloque se infieren automáticamente del `--destino` si la ruta
contiene el patrón `YYYY-N-BX` (ej: `2026-2-B1`). También se pueden pasar
explícitamente con `--periodo 2026-2 --bloque B1`.

## Integración con ClickUp

El skill extrae y organiza los archivos locales. ClickUp es el sistema
de registro para el seguimiento de completación de cada curso. **El
skill nunca importa código de `use-clickup`** — la integración ocurre
en el agente, que orquesta ambos skills.

- **`clickup.json`:** índice de space/folder/lists/tareas por período.
- **Tags canónicos:** ver `references/clickup-integracion.md` (tags
  de tipo, evaluación, soporte + prioridades).
- **Flujo:** `init` y `estado` preguntan al usuario si sincronizar;
  `cli_clickup.py --dry-run` permite previsualizar antes de confirmar.

## Configuración LLM

El skill usa modelos de lenguaje para formatear documentos y resumir videos.
La configuración se centraliza en `openrouter.json`:

- **`default_model`**: modelo principal (por defecto: `google/gemma-4-31b-it:free`)
- **`fallback_model`**: modelo de respaldo si el principal falla
- **`profiles`**: perfiles por tarea (`document_formatter`, `youtube_summarizer`)

Cada perfil define: `system_prompt`, `temperature`, `max_tokens`, `timeout`,
`chunking` (división automática de textos largos) y `model`/`fallback`
(`null` = hereda del nivel raíz).

**Variables de entorno en `.env`:**
- `OPENROUTER_API_KEY`: clave de API OpenRouter (requerida)
- `OPENROUTER_MODEL`: anula el modelo por defecto

**Jerarquía de ejecución:**
1. Agente nativo (`builtins.llm_complete`) → sin costo extra
2. OpenRouter API → requiere `OPENROUTER_API_KEY`
3. Sin LLM disponible → texto sin procesar

**Caché:** resultados LLM se cachean en `_cache/<sha256>.json` dentro
de cada carpeta de curso. Re-ejecuciones no gastan créditos en textos ya procesados.

**Verificación de créditos:** `openrouter.json` permite configurar
`credit_threshold` y `credit_check` para abortar si el saldo es insuficiente.

## Flujos de Trabajo

### gestionar-cursos init \<URL\> [\<URL2\> ...]

**Uso:** Inicializar uno o varios cursos desde URL(s) de Moodle.

**Pasos:**
1. Verificar sesión en Moodle
2. Navegar a la URL del curso proporcionada
3. Extraer estructura de la barra lateral (todas las secciones)
4. Navegar a "Introducción" y extraer:
   - Visión general del curso (texto para AGENTS.md)
   - Tabla PGA (DO-FR-66) — normalizar fechas a ISO 8601
   - Tabla de sesiones sincrónicas — validar enlaces Teams
   - Documentos introductorios: Módulo, Microcurrículo, y cualquier otro (PDF, DOCX, XLSX, PPTX)
   - Los documentos se descargan a `MATERIA/` y su texto se envía al LLM para limpieza + extracción de metadatos
   - Foros: Avisos, Foro de Consultas, Foro de Presentación — extraer TODAS las discusiones de primer nivel iniciadas por el profesor (solo la publicación original, no respuestas)
5. Por cada unidad en la barra lateral:
   - Expandir menús desplegables
   - Buscar actividades del PGA
   - Extraer descripción completa, instrucciones, materiales
   - Consolidar: PGA información + detalle de unidad = actividad completa
   - Detectar enlaces YouTube en páginas y módulos `url`, extraer subtítulos con `yt-dlp`, resumir con LLM
6. Descargar materiales (PDFs, documentos de apoyo)
7. Crear estructura de carpetas local
8. Generar archivos: AGENTS.md, CONTEXT.md, PGA.md, SITEMAP.md

**Salida:** Carpeta `[CÓDIGO]-nombre-en-kebab-case` con toda la estructura.

**Metadatos LLM:** `AGENTS.md` incluye sección `## Metadatos del Curso` con
objetivos, competencias, metodología, criterios de evaluación, unidades
temáticas y bibliografía extraídos automáticamente de los documentos
introductorios.

**Procesamiento paralelo:** Si se pasan múltiples URLs con `--parallel`,
cada curso se procesa en un subproceso independiente. El proceso padre
verifica la sesión una sola vez y lanza los subprocesos con `--no-browser`
para que compartan la misma instancia de Chrome CDP.

```bash
uv run python cli_init.py <url1> <url2> <url3> --parallel --destino .
```

**Re-inicialización:** Si el curso ya existe localmente, `init` detecta
`AGENTS.md` y redirige a sincronización selectiva:
- Refresca secciones marcadas `<!-- auto -->` desde Moodle.
- Preserva secciones marcadas `<!-- manual -->` (ej: PERIOD, BLOCK editados a mano).
- Documentos introductorios se vuelven a extraer y fusionan.

### gestionar-cursos clickup-sync \<PERIODO_DIR\>

**Uso:** Sincronizar la estructura local de todo un período con ClickUp.

```bash
uv run python cli_clickup.py "C:/Users/.../Universidad/2026-2-B1"
uv run python cli_clickup.py "C:/Users/.../Universidad/2026-2-B1" --dry-run
```

**Qué hace:**
1. Resuelve `folder.id` en el espacio "Universidad" (crea folder si no existe)
2. Por cada curso en `clickup.json` con `list_id: null`, resuelve/crea la lista
3. Por cada actividad **no sincronizada** crea tarea con tags y prioridad, usando
   `start_date` y `due_date` según la fuente de verdad (ver
   [Fuente de Verdad de Fechas](#fuente-de-verdad-de-fechas) más abajo):
   - **Primario:** `_cache/snapshot.json` (`fecha_apertura`/`fecha_cierre`)
     extraídas por `estado` de las páginas reales de Moodle.
   - **Secundario (fallback):** `PGA.md` para actividades no visitables
     (páginas, URLs) o si la snapshot no tiene fechas.
4. Actualiza `AGENTS.md` con `CLICKUP_LIST_ID` y `clickup.json` con los IDs resueltos
   y las fechas aplicadas (`start_date`/`due_date` ISO por tarea).
5. Si la tarea ya existe pero cambió la fecha (según snapshot), la actualiza
   automáticamente — **nunca** revierte una fecha real de Moodle por la del PGA.

> **⚠ No reviertas con el PGA:** la sección [Fuente de Verdad de Fechas](#fuente-de-verdad-de-fechas)
> explica por qué `PGA fecha_fin` no es autoritativa. Si `cli_clickup.py` se
> ejecuta sin snapshot fresca, ejecuta `estado` primero.

### gestionar-cursos estado \<CARPETA\>

**Uso:** Verificar cambios en el curso comparando contra la última fotografía
(`_cache/snapshot.json`). El agente ejecuta esto automáticamente si la
snapshot tiene más de 24h de antigüedad.

**Flujo:**
1. Cargar `_cache/snapshot.json` (creado por `init`)
2. Extraer barra lateral actual de Moodle
3. Comparar URLs → detectar actividades nuevas, eliminadas y existentes
4. En paralelo: un subproceso por unidad visita cada `quiz`/`assign`/`forum`/
   `lesson`/`workshop` y extrae fechas de `div[data-region='activity-dates']`
   (Abrió/Cierra/Vencimiento) → ISO 8601 en hora Colombia (UTC-5)
5. Comparar fechas extraídas vs snapshot → detectar cambios de deadline
6. Guardar nueva snapshot actualizada (autoritativa para ClickUp)
7. Reportar diff

> La snapshot es la **fuente de verdad** para fechas. `cli_clickup.py` debe
> preferirla sobre `PGA.md` (ver [Fuente de Verdad de Fechas](#fuente-de-verdad-de-fechas)).

**Salida:** Reporte en conversación:

```markdown
## 🆕 Actividades nuevas (2)
- Actividad X (quiz) — Unidad 3
- Foro Y (forum) — Unidad 2

## 📅 Fechas modificadas (1)
- Primer parcial (Unidad 1)
  - Cierre: 2026-02-15 → **2026-02-22**

## 🗑️ Eliminadas/ocultas (1)
- ~~Actividad antigua~~ (Unidad 1)
```

Si se usa `--sync`, el agente puede re-ejecutar `init` para descargar el
contenido de las actividades nuevas. Las fechas modificadas se reflejan en
la snapshot automáticamente.

El agente también usa `use-clickup` para actualizar las tareas de ClickUp
si detecta cambios de fecha o nuevas actividades.

### gestionar-cursos foros \<CARPETA\>

**Uso:** Extraer foros evaluables (>0% en título) y los hilos principales
de compañeros (sin replies). El output va a `Unidad-X/Foros/<slug>.md`.
Usa cache por `discuss_id` (query string de `discuss.php`) — re-ejecuciones
no re-abren hilos ya guardados.

**Cuándo correrlo:** durante `init` ya se invoca automáticamente para
foros evaluables de cada unidad. También se puede correr manualmente
cuando quieras actualizar los hilos tras varios días, o después de que
`cli_estado.py` reporte hilos nuevos en foros.

```bash
cd gestionar-cursos/scripts
uv run python cli_foros.py "C:/.../2026-2-B1/MATERIA"
uv run python cli_foros.py "C:/.../2026-2-B1/MATERIA" --dry-run
```

**Qué extrae por foro (si es evaluable, regex `\(\d+%\)` con >0):**
título + %, vencimiento, indicaciones, actividad a realizar, y hasta
20 hilos principales (título, autor, fecha, último mensaje, réplicas,
URL) con el primer post completo de cada uno. Foros introductorios
(Avisos, Consultas, Presentación) NO se procesan aquí — siguen yendo
a `COMUNICACION/`.

Ver `references/foros-evaluables.md` para detalle de selectores HTML,
formato de cache, casos edge, y el cap de 20.

### gestionar-cursos calificaciones \<CARPETA\>

**Uso:** Extraer calificaciones del **gradebook** del estudiante en un
curso Moodle. Aplica a todos los items evaluables del curso: cuestionarios,
lecciones, talleres (envío + evaluación), tareas, foros. Actualiza
`_cache/calificaciones_<courseid>.json`, agrega campo `calificacion` en
cada actividad del `snapshot.json`, e inyecta sección `## Calificación`
en el archivo `.md` de cada actividad.

```bash
cd gestionar-cursos/scripts
uv run python cli_calificaciones.py "C:/.../2026-2-B1/2607B04G1-línea-de-énfasis-1"
uv run python cli_calificaciones.py "C:/.../2026-2-B1/2607B04G1-línea-de-énfasis-1" --dry-run
```

**Cuándo correrlo:**
- Después de `estado` (que refresca fechas).
- Tras un parcial o tarea calificada por el docente.
- Antes de la sesión sincrónica para ver el avance del curso.

**Orden correcto del flujo de sincronización:**

```bash
# 1) Refrescar fechas
uv run python cli_estado.py "C:/.../2026-2-B1/<curso>"

# 2) Capturar calificaciones (sobre snapshot recien refrescado)
uv run python cli_calificaciones.py "C:/.../2026-2-B1/<curso>"

# 3) Sincronizar tareas con ClickUp (crear/actualizar fechas, tags)
uv run python cli_clickup.py "C:/.../2026-2-B1"

# 4) Sincronizar calificaciones capturadas → ClickUp (status + comentario)
uv run python sync_calificaciones_clickup.py "C:/.../2026-2-B1/<curso>"
```

`cli_estado.py` preserva el campo `calificacion` y el
`calificaciones_capturadas` al re-escribir `snapshot.json`. Re-ejecutar
`estado` después de `calificaciones` no borra las notas. **Orden
inverso = bug**: si se ejecuta `calificaciones` antes que `estado`, las
calificaciones se preservan; pero si se ejecuta `calificaciones` y
luego `estado` sin preservar, las calificaciones se pierden. (Desde
2026-2-B1 está arreglado en `guardar_snapshot`.)

**Lo que captura por actividad:**

| Campo | Fuente Moodle |
|-------|---------------|
| `nota` | Calificación en escala del rango |
| `estado` | Aprobado / Reprobado / Pendiente (icono `fa-check text-success` / `fa-remove text-danger`) |
| `rango` | Rango calificable (ej. `0–5`) |
| `porcentaje` | % sobre el rango |
| `aporte_curso` | % ya ponderado al total del curso |
| `ponderacion_categoria` | Ponderación dentro de la categoría del curso |
| `feedback` | Retroalimentación del docente |

**Match de archivos `.md`:** por nombre normalizado + alias canónicos
(`Prueba Inicial` → `PruebaInicial.md`, `Primer Parcial` → `Parcial-1.md`,
etc.). Si una actividad del gradebook no tiene `.md` local (típico:
H5P `Contenido interactivo`), el script lo reporta como warning pero
no falla.

**Cache:** el HTML crudo se guarda en
`_cache/gradebook_<courseid>.html` para auditoría, y el JSON
estructurado en `_cache/calificaciones_<courseid>.json`. Re-ejecuciones
sobre-escriben — no hay merge acumulativo.

### gestionar-cursos sync-clickup-calificaciones \<CARPETA\>

**Uso:** Para cada tarea calificada en el `snapshot.json` del curso,
marca la tarea de ClickUp como **"calificado"** (status closed) y deja
un comentario con el detalle de la nota. Es idempotente: re-ejecuciones
no duplican status ni comentarios.

```bash
cd gestionar-cursos/scripts
uv run python sync_calificaciones_clickup.py "C:/.../2026-2-B1/<curso>"
uv run python sync_calificaciones_clickup.py "C:/.../2026-2-B1/<curso>" --dry-run
```

**Prerrequisito:** ejecutar `cli_calificaciones.py` primero para poblar
`snapshot.json:actividades[*].calificacion`. Si no hay calificaciones
capturadas, el script no hace nada (no hay qué sincronizar).

**Cuándo correrlo:**
- Después de `cli_calificaciones.py` cuando aparecen nuevas notas
  (parcial calificado, tarea devuelta, etc).
- En el flujo de revisión de fin de semana para tener el tablero de
  ClickUp al día.

**Qué hace por cada tarea con `calificacion.nota`:**

1. **Cruza por nombre** entre `snapshot.json` y `clickup.json` (con
   matching exacto + flexible). Si no encuentra `task_id`, warning.
2. **Verifica idempotencia**:
   - `tarea_ya_calificada`: ¿status ya es "calificado"?
   - `tiene_comentario_sync`: ¿hay un comentario con tag
     `[calificaciones-auto]`?
   - Si ambas → SKIP (no duplica status ni comentario).
3. **PUT /task/{id}** con `{"status": "calificado"}` (usa el NOMBRE,
   no el status_id — la API de ClickUp rechaza IDs con 400).
4. **POST /task/{id}/comment** con formato:
   ```
   [calificaciones-auto] Calificación sincronizada desde Moodle

   - **Curso:** LÍNEA DE ÉNFASIS 1 - 2607B04G1
   - **Actividad:** Primer Parcial (25%)
   - **Nota:** 4,80 / 0–5 (96,00 %)
   - **Estado:** Aprobado
   - **Aporte al curso:** 24,00 %
   - **Capturado:** 2026-07-17T01:21:11
   ```

**Status personalizado:** el script busca el status "calificado" en el
space Universidad (id `901311224662`). El status se creó manualmente
en el space como tipo `closed`. Si no existe, el script falla con
lista de statuses disponibles. Otros espacios no-Universidad necesitan
su propio status (o el script debe parametrizar el nombre).

**Lección (2026-2-B1, LPA 1 + Línea de Énfasis 1):** la API de
ClickUp `PUT /task/{id}` rechaza el `status_id` con 400 Bad Request
cuando se envía el `id` (`p901311224662_MhIABMss`). Hay que enviar el
**nombre** del status (`"calificado"`). El `client.py` no documenta
esto explícitamente; el bug se manifiesta como "el status se queda en
pendiente aunque la respuesta sea 200" o como 400 directo.

## Política de Errores

**Resiliente — nunca falla completamente.**

| Escenario | Comportamiento |
|-----------|----------------|
| Moodle caído / tiempo de espera | Reintentar 3 veces (1s, 2s, 4s). Si persiste, error con mensaje. |
| Actividad no encontrada | Advertencia + marcar `[DETALLE_NO_ENCONTRADO]`. Continuar. |
| PDF bloqueado | Advertencia + guardar enlace en lugar de archivo. No detener. |
| H5P no carga | Omitir proxy + enlace original en el mapa del sitio. |
| Sesión expirada | Detectar redirección a inicio de sesión → pausar + pedir volver a iniciar sesión. |
| Cambio en estructura HTML | Guardar HTML sin procesar para depuración + advertencia. Procesar lo posible. |
| LLM no disponible | Usar texto extraído sin formatear. Continuar sin metadatos. |
| OpenRouter sin créditos | Abortar llamadas LLM si saldo < umbral configurado. |

## Formato de Fechas

Todas las fechas se normalizan a **ISO 8601** (`YYYY-MM-DD`).

En archivos markdown se muestra dual:
```markdown
| Actividad | Fecha Inicio | Fecha Fin |
|-----------|--------------|-----------|
| Prueba Inicial | 26/1/2026 (2026-01-26) | 1/2/2026 (2026-02-01) |
```

## Fuente de Verdad de Fechas

**Regla de oro: la fuente de verdad operativa de las fechas de entrega NO es
el PGA, sino las fechas de apertura y cierre configuradas por el profesor en
cada actividad de Moodle.**

Flujo:
1. `init` extrae el PGA como referencia de planeación.
2. `estado` extrae las fechas reales de Moodle → `_cache/snapshot.json`.
3. `cli_clickup.py` prefiere `snapshot.json` sobre `PGA.md`.
4. Tras sincronizar, actualizar `PGA.md` para que refleje las fechas reales.

Detalle, selectores HTML, y la lección dura del 2026-2-B1 en
`references/fechas-fuente-de-verdad.md`.

## Heurísticas de Extracción

Reglas que el skill aplica al procesar cada tipo de módulo
(Teams, H5P, pluginfile.php, nombres de actividades). Ver detalle
en `references/extraccion-heuristicas.md`.

Resumen:
- **Teams:** solo URLs `teams.microsoft.com/l/meetup-join/`. Si no,
  marcar como pendiente.
- **forcedownload:** añadir `?forcedownload=1` o `&forcedownload=1`
  a cualquier URL de `pluginfile.php`.
- **H5P:** crear proxy HTML local con iframe + `h5p-resizer.js`.
- **Nombres de actividades:** auto-acortar patrones como
  `Actividad de seguimiento (Calificable 10%) Disponible...` →
  `Seguimiento[10%].md`.

## Estructura de Carpetas Local

```
2026-2-B1/                         # Raíz del período académico
├── clickup.json                   # Índice ClickUp del período (UNO para todas las materias)
├── [CÓDIGO]-NOMBRE-DEL-CURSO/
│   ├── _cache/                    # Caché LLM + snapshot.json
│   ├── AGENTS.md                  # Metadatos + visión general + metadata LLM
│   ├── CONTEXT.md                 # Contexto extenso: documentos, PGA, sesiones
│   ├── SITEMAP.md                 # Enlaces permanentes de Moodle
│   ├── PGA.md                     # Tabla de actividades (fechas ISO)
│   ├── MATERIA/
│   ├── Modulo.pdf
│   ├── Microcurriculo.pdf
│   └── ...                       # Otros documentos del profesor
├── COMUNICACION/
│   ├── YYYYMMDD_Avisos.md
│   ├── YYYYMMDD_Foro_Consultas.md
│   └── YYYYMMDD_Foro_Presentacion.md
├── Unidad-1/
│   ├── contenido/
│   │   ├── Conoce_tu_profesor.md
│   │   └── Vision_general_del_curso.md
│   ├── materiales/
│   │   ├── documento.pdf
│   │   ├── presentacion.html      # H5P proxy
│   │   └── Seguimiento_YouTube.md # Resumen de video YouTube
│   ├── actividades/
│   │   ├── Seguimiento[10%].md
│   │   ├── Parcial-1[25%].md
│   │   └── Parcial-3[25%].md
│   └── Foros/
│       └── Foro_1_Seguridad_en_aplicaciones_web_6.md
├── Unidad-2/
│   └── ...
└── Unidad-3/
    └── ...
```

## AGENTS.md - Contenido

```markdown
# [Nombre del Curso]

> Índice de curso para agentes. Ver detalles en CONTEXT.md.

## Identidad
- **CODIGO**: [Código]
- **URL**: [URL permanente del curso]
- **PERIODO**: 2026-2
- **BLOQUE**: B1
- **SEMANAS**: [PENDIENTE]
- **INICIO**: [YYYY-MM-DD]
- **FIN**: [YYYY-MM-DD]
- **INICIALIZADO**: [Fecha de inicialización]

## Resumen
[Primer párrafo de la visión general del curso]

## Metadatos del Curso
[Extraídos por LLM de Módulo y Microcurrículo]

### Objetivos
- ...

### Competencias
- ...

### Metodología
...

### Criterios de Evaluación
- ...

### Unidades Temáticas
- ...

### Bibliografía
- ...

## Sesiones Sincrónicas
| Descripción | Enlace Teams | Fecha | Hora | Grabaciones |
|-------------|-------------|-------|------|-------------|

## Índice Local
- [Unidad 1](Unidad-1/)
  - [Materiales](Unidad-1/materiales/)
  - [Actividades](Unidad-1/actividades/)
  - [Contenido](Unidad-1/contenido/)

## Archivos de Contexto
- [CONTEXT](CONTEXT.md)
- [PGA](PGA.md)
- [SITEMAP](SITEMAP.md)
- [COMUNICACION](COMUNICACION/)
```

## Archivos del Skill

### Puntos de Entrada (CLI)

script: `cli_init.py` — entry point principal que orquesta el pipeline completo importando 17 scripts: navegación (`browser_api`, `navegador_cdp`, `navegador_requests`), extracción por tipo de módulo (`extractor_modulos`, `extractor_foro`, `extractor_documentos`, `extractor_youtube`), scaffolding (`scaffold_curso`, `parsear_pga`, `parsear_sesiones`), procesamiento LLM (`llm_api`, `openrouter_client`, `formatear_llm`), y control de sesión (`moodle_session`, `verificar_sesion`, `checkpoint`).

| Archivo | Propósito |
|---------|-----------|
| `cli_init.py` | Inicializar curso(s) desde URL(s) de Moodle |
| `cli_estado.py` | Verificar estado y sincronización |
| `cli_calificaciones.py` | Extraer calificaciones del gradebook e inyectar `## Calificación` en `.md` |
| `sync_calificaciones_clickup.py` | Sincronizar calificaciones Moodle → ClickUp (status='calificado' + comentario) |
| `cli_clickup.py` | Sincronizar cursos locales con ClickUp (IDs, tareas, tags) |

### Extracción de Moodle
| Archivo | Propósito |
|---------|-----------|
| `navegador_cdp.py` | Navegador Chrome DevTools Protocol + Selenium |
| `navegador_requests.py` | Backend alternativo: requests + BS4 sin navegador real |
| `browser_api.py` | Capa de abstracción IDE ↔ CDP |
| `moodle_session.py` | Exportación de cookies Selenium → requests |
| `verificar_sesion.py` | Detección de sesión activa en Moodle |
| `extractor_modulos.py` | Extractores por tipo (page, quiz, forum, resource, folder, hvp, assign, url) |
| `extractor_foro.py` | Discusiones de foros del profesor (flujo intro/Avisos/Consultas) |
| `extractor_foro_evaluable.py` | Foros evaluables (>0%): metadata + hilos principales, cap 20, cache por `discuss_id` |
| `cli_foros.py` | CLI: `gestionar-cursos foros <CARPETA>` — renderiza foros evaluables a `Unidad-X/Foros/` |
| `_procesar_foro_evaluable.py` | Wrapper usado por `cli_init` para procesar un foro evaluable dentro del loop por actividad |
| `extractor_documentos.py` | PDF/DOCX/XLSX/PPTX → texto |
| `extractor_youtube.py` | Subtítulos YouTube vía yt-dlp + resumen LLM |
| `parsear_pga.py` | Tabla DO-FR-66, fechas ISO 8601 |
| `parsear_sesiones.py` | Cronograma con enlaces reales Teams |
| `scaffold_curso.py` | Estructura de carpetas, AGENTS.md, CONTEXT.md, SITEMAP.md |
| `checkpoint.py` | Punto de control `.progress.json` para reanudación |

### LLM
| Archivo | Propósito |
|---------|-----------|
| `openrouter_client.py` | Cliente OpenRouter con caché, fragmentación, reintentos, verificación de créditos |
| `llm_api.py` | Abstracción agente nativo → OpenRouter como respaldo |
| `formatear_llm.py` | Formateo de documentos + extracción de metadatos JSON |
| `openrouter.json` | Configuración centralizada: modelos, instrucciones, umbrales (raíz del skill) |

### Utilidades
| Archivo | Propósito |
|---------|-----------|
| `sincronizar_curso.py` | Detección de cambios Moodle contra local |
| `verificar_integridad.py` | Validación de archivos locales |
| `_extraer_fechas_unidad.py` | Subproceso: extrae fechas de quiz/assign por unidad |
| `detectar_plataforma.py` | Auto-detección de herramienta de navegación |
| `crear_proxy_h5p.py` | Generador de HTML proxy para contenido H5P |
| `descargar_materiales.py` | Descarga con `forcedownload` |
| `extraer_unidad.py` | Extracción a nivel de unidad |
| `verify.py` | Verificación de integridad del espacio de trabajo |
| `debug_profesor.py` | Utilidad de depuración para detección de profesor |
