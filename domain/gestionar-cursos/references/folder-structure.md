# Estructura de Carpetas Local

Diagrama canonico del arbol de archivos que `gestionar-cursos init`
genera para un periodo academico. El skill mantiene este formato
constante; cualquier deviation es un bug a reportar.

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

## Reglas

- `clickup.json` vive en la **raiz del periodo** y es UN SOLO archivo
  para todas las materias. Cada curso referencia su `list_id` desde
  ahi.
- Cada carpeta de curso (`[CÓDIGO]-NOMBRE-DEL-CURSO/`) tiene su
  propio `AGENTS.md`, `CONTEXT.md`, `SITEMAP.md`, `PGA.md` y
  `_cache/`.
- `COMUNICACION/` agrupa los foros introductorios (Avisos, Consultas,
  Presentacion) que NO son evaluables. Los foros evaluables van
  dentro de su `Unidad-X/Foros/`.
- Los nombres de archivos de actividades siguen el patron
  `<TituloNormalizado>[<porcentaje>%].md` (ver
  `references/extraccion-heuristicas.md` para las reglas de
  normalizacion).
- `_cache/` guarda HTML crudo (auditoria), `snapshot.json` (fuente
  de verdad de fechas), `calificaciones_<courseid>.json`, y
  `foros_cache.json`. NO se commitea.
