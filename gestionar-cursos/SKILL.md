---
name: gestionar-cursos
description: >-
  Extrae información de cursos Moodle Uniremington y organiza estructura
  de carpetas local. Úsalo para inicializar cursos, sincronizar contenido
  o verificar estado de un curso vs Moodle.
metadata:
  version: "3.0.0"
  language: es-CO
  risk_tier: LOW
---

# /gestionar-cursos

Skill standalone para gestión de cursos universitarios en la plataforma
Moodle de Uniremington (aulavirtual.uniremington.edu.co).

## Autenticación

Antes de cualquier navegación:

1. Navegar a `https://aulavirtual.uniremington.edu.co/my/`
2. Verificar estado:
   - **NO AUTENTICADO**: URL contiene `login/index.php` o texto "Usted no se ha identificado"
     → Detener y pedir al usuario: "Por favor haz login en Moodle manualmente"
   - **AUTENTICADO**: Ver nombre "Andres Felipe Rendon Hernandez" o heading "Área personal"
     → Continuar

## Detección de Plataforma

El skill detecta automáticamente qué tool de navegación está disponible:

1. **browser_tool** → VS Code / Antigravity (navegación headless integrada)
2. **open_browser** → OpenCode / fallback (ventana externa del SO)
3. **Ninguna** → Error: "No hay tool de navegación disponible"

## Workflows

### /gestionar-cursos init <URL>

**Uso:** Inicializar un curso nuevo desde URL de Moodle.

**Pasos:**
1. Verificar sesión en Moodle
2. Navegar a la URL del curso proporcionada
3. Extraer estructura del sidebar (todas las secciones)
4. Navegar a "Introducción" y extraer:
   - Visión general del curso (texto para AGENTS.md)
   - Tabla PGA (DO-FR-66) — normalizar fechas a ISO 8601
   - Tabla de sesiones sincrónicas — validar links Teams
   - Documentos: Módulo, Microcurrículo
   - Foros: Avisos, Foro de Consultas, Foro de Presentación
5. Por cada unidad en el sidebar:
   - Expandir menús desplegables
   - Buscar actividades del PGA
   - Extraer descripción completa, instrucciones, materiales
   - Consolidar: PGA info + detalle de unidad = actividad completa
6. Descargar materiales (PDFs, documentos de apoyo)
7. Crear estructura de carpetas local
8. Generar archivos: AGENTS.md, sitemap.md, PGA.md, SESIONES_SINCRONAS.md

**Output:** Carpeta local con toda la estructura organizada.

### /gestionar-cursos estado <CARPETA>

**Uso:** Verificar estado actual del curso comparando con Moodle.

**Internamente ejecuta:**
1. `sincronizar_curso.py` — detecta cambios en Moodle vs local
   - Nuevas actividades
   - Fechas modificadas
   - Nuevos materiales
   - Links de grabaciones publicados
2. `verificar_integridad.py` — valida archivos locales
   - Archivos faltantes
   - Links rotos
   - Actividades sin detalle

**Output:** Reporte en conversación (no persistido):

```markdown
# Estado: [Nombre del Curso]

## 🔄 Sincronización
- Última sync: [timestamp]
- Cambios detectados: [N]

| Tipo | Actividad | Acción |
|------|-----------|--------|
| Fecha cambiada | Primer Parcial | 8/2/2026 → 15/2/2026 |
| Nueva | Foro Unidad 2 | Agregada |

## ✅ Verificación
- Archivos locales: [N]/[N] OK
- Links rotos: [N]
- Actividades sin detalle: [N]

## 📅 Próximas entregas (7 días)
| Fecha | Actividad | Unidad |
|-------|-----------|--------|
| 1/2/2026 | Cuestionario evaluativo | 1 |

## ⚠️ Advertencias
- [N] actividad(es) no encontrada(s) en Moodle (puede estar oculta)
```

## Política de Errores

**Resiliente — nunca falla completamente.**

| Escenario | Comportamiento |
|-----------|----------------|
| Moodle caído / timeout | Reintentar 3 veces (1s, 2s, 4s). Si persiste, error con mensaje. |
| Actividad no encontrada | Warning + marcar `[DETALLE_NO_ENCONTRADO]`. Continuar. |
| PDF bloqueado | Warning + guardar link en lugar de archivo. No detener. |
| H5P no carga | Skip proxy + link original en sitemap. |
| Sesión expirada | Detectar redirect a login → pausar + pedir re-login. |
| Cambio en estructura HTML | Guardar raw para debug + warning. Parsear lo posible. |

## Formato de Fechas

Todas las fechas se normalizan a **ISO 8601** (`YYYY-MM-DD`).

En archivos markdown se muestra dual:
```markdown
| Actividad | Fecha Inicio | Fecha Fin |
|-----------|--------------|-----------|
| Prueba Inicial | 26/1/2026 (2026-01-26) | 1/2/2026 (2026-02-01) |
```

## Heurísticas de Extracción

### Links Teams

SOLO capturar links que apunten a `teams.microsoft.com/l/meetup-join/`.

Si el link usa acortadores o redirección de Moodle (`mod/url/view.php`), **ignorar**.

Si no hay link directo, marcar como `[PENDIENTE: Link no seguro o inexistente]`.

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

Etiquetar en sitemap como `[Interactivo]`.

### Links Grabaciones

Los links de grabaciones NO existen al inicio del curso. Se publican después.

En workflow `estado`, verificar si aparecieron nuevos links de grabaciones y actualizar SESIONES_SINCRONAS.md.

## Estructura de Carpetas Local

```
[CURSO_CODE]/
├── AGENTS.md                    # Metadatos + visión general del curso
├── README.md                    # Resumen para humano
├── sitemap.md                   # Links permanentes de Moodle
├── PGA.md                       # Tabla de actividades (fechas ISO)
├── SESIONES_SINCRONAS.md        # Cronograma con links Teams + grabaciones
├── MATERIA/
│   ├── Modulo.pdf
│   └── Microcurriculo.pdf
├── COMUNICACION/
│   ├── Avisos.md
│   ├── Foro_Consultas.md
│   └── Foro_Presentacion.md
├── Unidad-1/
│   ├── materiales/
│   │   ├── documento.pdf
│   │   └── presentacion.html    # H5P proxy
│   └── actividades/
│       ├── Prueba_Inicial.md
│       ├── Cuestionario_evaluativo.md
│       └── Primer_Parcial.md
├── Unidad-2/
│   └── ...
└── Unidad-3/
    └── ...
```

## AGENTS.md - Contenido

```markdown
# [Nombre del Curso]

## Identidad
- **COURSE_NAME**: [Nombre completo]
- **COURSE_CODE**: [Código]
- **PERIOD**: [Periodo, ej: 2026-1]
- **BLOCK**: [Bloque]
- **MOODLE_URL**: [URL permanente del curso]
- **INITIALIZED**: [Fecha de inicialización]

## Alcance del curso
[Texto extraído de "Visión general del curso" en la sección Introducción]

## Estructura
- Unidades: [N]
- Semanas: [N]
- Fecha inicio: [YYYY-MM-DD]
- Fecha fin: [YYYY-MM-DD]

## Links clave
- [PGA](PGA.md)
- [Sesiones Sincrónicas](SESIONES_SINCRONAS.md)
- [Sitemap](sitemap.md)
```