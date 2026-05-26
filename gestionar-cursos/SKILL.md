---
name: gestionar-cursos
description: >-
  Extrae información de cursos Moodle Uniremington y organiza estructura
  de carpetas local. Usa cuando necesites inicializar cursos, sincronizar
  contenido o verificar estado de un curso vs Moodle.
language: es-CO
---

# /gestionar-cursos

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

1. **browser_tool** → VS Code / Antigravity (navegación integrada sin interfaz gráfica)
2. **open_browser** → OpenCode IDE / alternativa (ventana externa del SO)
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

El skill extrae y organiza los archivos locales. ClickUp es el sistema de
registro para el seguimiento de completación de cada curso. **El skill nunca
importa código de `use-clickup`.** La integración ocurre en el agente, que
orquesta ambos skills.

**`clickup.json`:** un archivo por período académico en la raíz del workspace.
Indexa space, folder, listas y tareas de todas las materias de ese período.
`init` lo crea o lo extiende con la entrada del nuevo curso.

**Estructura en ClickUp:**
```
Universidad (space, id fijo: 901311224662)
└── 2026-2-B1 (folder, uno por período-bloque)
    ├── HUMANIDADES II - 2601B04G1 (list, una por curso)
    └── BASES DE DATOS 2 - 2601B05G2 (list)
```

**Flujo del agente tras `init`:**
1. Leer `PERIODO`, `BLOQUE` y `CLICKUP_LIST_ID` de AGENTS.md
2. Si `CLICKUP_LIST_ID` es `[PENDIENTE]`: leer `clickup.json`, encontrar el
   curso por código, resolver `folder.id` y `list.id` vía `use-clickup`,
   guardar IDs en ambos archivos
3. Por cada actividad del PGA que no esté en `clickup.json → tasks`:
   crear tarea vía `use-clickup` con `due_date`, tags y prioridad

**Flujo del agente tras `estado`:**
1. Ejecutar `cli_estado.py` → detectar cambios de fecha y nuevas actividades
2. `use-clickup actualizar-tarea` para fechas modificadas
3. `use-clickup crear-tarea` para actividades nuevas

### Tags del Skill

El skill define el conjunto canónico. `use-clickup` solo transporta los tags
a la API; no define cuáles son válidos.

**Tags de tipo de actividad (determinan prioridad):**

| Tag | Criterio | Prioridad |
|-----|----------|-----------|
| `parcial` | Ponderación ≥15% o nombre contiene "parcial" | `urgente` |
| `quiz` | Ponderación <15% o "cuestionario"/"prueba" | `normal` |
| `actividad` | Assignment, seguimiento, tarea, trabajo | `alta` |
| `foro` | Foro de discusión | `normal` |

**Tags de evaluación:**

| Tag | Significado |
|-----|------------|
| `evaluable` | Tiene nota en el PGA |
| `no-evaluable` | Formativo, sin calificación |

**Tags de soporte (combinables):**

| Tag | Cuándo |
|-----|--------|
| `grupal` | Trabajo en equipo |
| `entregable` | Requiere subir archivo o enlace |
| `lectura` | Leer material obligatorio |
| `repaso` | Estudiar para parcial/quiz |
| `documento` | Redactar informe, ensayo |
| `investigar` | Buscar fuentes, datos |
| `practica` | Ejercicios, código, laboratorio |
| `exposicion` | Preparar presentación |
| `participacion` | Requiere intervenir en foro/clase |

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

### /gestionar-cursos init \<URL\> [\<URL2\> ...]

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

### /gestionar-cursos estado \<CARPETA\>

**Uso:** Verificar cambios en el curso comparando contra la última fotografía
(`_cache/snapshot.json`). El agente ejecuta esto automáticamente si la
snapshot tiene más de 24h de antigüedad.

**Flujo:**
1. Cargar `_cache/snapshot.json` (creado por `init`)
2. Extraer barra lateral actual de Moodle
3. Comparar URLs → detectar actividades nuevas, eliminadas y existentes
4. En paralelo: un subproceso por unidad visita cada `quiz`/`assign` y extrae fechas
5. Comparar fechas extraídas vs snapshot → detectar cambios de deadline
6. Guardar nueva snapshot actualizada
7. Reportar diff

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

## Heurísticas de Extracción

### Enlaces Teams

SOLO capturar enlaces que apunten a `teams.microsoft.com/l/meetup-join/`.

Si el enlace usa acortadores o redirección de Moodle (`mod/url/view.php`), **ignorar**.

Si no hay enlace directo, marcar como `[PENDIENTE: Enlace no seguro o inexistente]`.

### forcedownload

Al descargar cualquier archivo de `pluginfile.php`, añadir:
- Si URL tiene `?`: `&forcedownload=1`
- Si URL no tiene `?`: `?forcedownload=1`

### H5P

Crear proxy HTML local:
```html
<!DOCTYPE html>
<html>
<head>
    <title>[Nombre]</title>
    <style>body { margin: 0; display: flex; justify-content: center; background: #000; overflow: hidden; height: 100vh; }</style>
</head>
<body>
    <iframe src="https://aulavirtual.uniremington.edu.co/mod/hvp/embed.php?id=[ID]"
            width="100%" height="100%" style="border:0;"
            allowfullscreen="allowfullscreen"></iframe>
    <script src="https://aulavirtual.uniremington.edu.co/mod/hvp/library/js/h5p-resizer.js" charset="UTF-8"></script>
</body>
</html>
```

Etiquetar en el mapa del sitio como `[Interactivo]`.

### Enlaces de Grabaciones

Los enlaces de grabaciones NO existen al inicio del curso. Se publican después.

En el flujo `estado`, verificar si aparecieron nuevos enlaces de grabaciones y
actualizar SESIONES_SINCRONAS.md.

### Nombres de Archivos de Actividades

Los nombres largos con patrones procesables se acortan automáticamente:

- `Actividad de seguimiento (Calificable 10%) Disponible del 2 al 8 de febrero`
  → `Seguimiento[10%].md`
- `Unidad 1. Primer parcial (Calificable 25%) Disponible del 9 al 15 de febrero`
  → `Parcial-1[25%].md`
- `Prueba inicial (No calificable) Disponible hasta el 1 de febrero`
  → `PruebaInicial[N/A].md`

Las fechas ya quedan reflejadas dentro del contenido.

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
│   └── actividades/
│       ├── Seguimiento[10%].md
│       ├── Parcial-1[25%].md
│       └── Parcial-3[25%].md
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
| Archivo | Propósito |
|---------|-----------|
| `cli_init.py` | Inicializar curso(s) desde URL(s) de Moodle |
| `cli_estado.py` | Verificar estado y sincronización |

### Extracción de Moodle
| Archivo | Propósito |
|---------|-----------|
| `navegador_cdp.py` | Navegador Chrome DevTools Protocol + Selenium |
| `browser_api.py` | Capa de abstracción IDE ↔ CDP |
| `moodle_session.py` | Exportación de cookies Selenium → requests |
| `verificar_sesion.py` | Detección de sesión activa en Moodle |
| `extractor_modulos.py` | Extractores por tipo (page, quiz, forum, resource, folder, hvp, assign, url) |
| `extractor_foro.py` | Discusiones de foros del profesor |
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
