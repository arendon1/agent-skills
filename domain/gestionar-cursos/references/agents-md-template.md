# Plantilla AGENTS.md del curso

Plantilla que `gestionar-cursos init` usa para generar el
`AGENTS.md` de cada curso. Es un indice de alto nivel: el detalle
extenso vive en `CONTEXT.md`.

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

## Secciones marcadas con comentarios auto

`gestionar-cursos init` distingue dos tipos de secciones:

- `<!-- auto -->` — el skill las refresca desde Moodle en cada
  re-inicializacion selectiva. Usar para metadata, resumen, PGA,
  sesiones sincronicas, indice local.
- `<!-- manual -->` — el skill las preserva tal cual. Usar para
  notas personales, PERIOD/BLOCK editados a mano, decisiones
  pedagogicas del docente que el script no debe tocar.

Si una seccion no tiene marcador explicito, se trata como `auto` y
se sobre-escribe en la proxima re-inicializacion.
