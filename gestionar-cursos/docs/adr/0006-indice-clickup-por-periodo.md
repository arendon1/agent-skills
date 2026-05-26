# Índice ClickUp por período académico

`gestionar-cursos` y `use-clickup` son skills independientes que no se
importan entre sí. La integración ocurre en el agente, que orquesta ambos.
El skill escribe un `clickup.json` por período académico como contrato de
datos; el agente lo lee y completa los IDs vía `use-clickup`.

## Decisiones

### 1. Un `clickup.json` por período académico

Vive en la raíz del workspace (`2026-2-B1/clickup.json`), no uno por curso.
Indexa `space`, `folder`, y todas las `courses` de ese período con sus
`list_id` y `tasks`. Evita duplicar configuración de tags y prioridades
en cada curso.

### 2. `gestionar-cursos` no importa `use-clickup`

El skill escribe `clickup.json` con `space.id` fijo (`901311224662`),
`folder.id = null`, y `list_id = null` para cada curso. No hace llamadas
a la API de ClickUp. El agente, en un paso posterior, lee el archivo,
resuelve los IDs faltantes vía subagentes de `use-clickup`, y escribe
los valores de vuelta.

**Rechazado:** importar `use-clickup/scripts/client.py` desde `cli_init.py`.
Crea acoplamiento entre skills, complica el testeo independiente, y viola
el principio de que cada skill es autónomo.

### 3. Tags definidos por `gestionar-cursos`

El skill define el conjunto canónico de 15 tags (`parcial`, `quiz`,
`actividad`, `foro`, `evaluable`, `no-evaluable`, `grupal`, `entregable`,
`lectura`, `repaso`, `documento`, `investigar`, `practica`, `exposicion`,
`participacion`). `use-clickup` solo transporta los tags a la API; no
impone cuáles son válidos. El mapeo de tipo de actividad → tags base
y prioridad está en `clickup.json → activity_tags` y `priority_map`.

### 4. `space.id` fijo

El espacio "Universidad" tiene ID `901311224662` (resuelto de la API).
Está hardcodeado en `cli_init.py` como constante. Si cambia, se actualiza
en un solo lugar. El agente no necesita resolverlo cada vez.

## Consecuencias

- `clickup.json` se crea en el `--destino` (raíz del período), no dentro
  de la carpeta del curso.
- El agente debe sincronizar `CLICKUP_LIST_ID` en cada `AGENTS.md` después
  de resolver las listas.
- `use-clickup` debe aceptar los 15 tags definidos aquí (actualmente su
  `TAGS_VALIDOS` tiene un conjunto diferente que debe alinearse).
