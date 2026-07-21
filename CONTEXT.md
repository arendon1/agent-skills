# CONTEXT — Ubiquitous Language

Glosario canonico del repo `agent-skills`. Cualquier termino usado en
plan artifacts, codigo o docs debe aparecer aca o en una entrada mas
especifica. Fuzzy terms se afilan; sinonimos se consolidan en una
entrada canonica.

Reglas:
- Este archivo es SOLO glosario. No es spec, ni pad de diseno, ni
  bitacora de implementacion.
- Cada termino lleva un "_Evitar_:" con sinonimos descartados.
- Cambios aqui reflejan consensos cristalizados, no opiniones
  individuales.

## sync_plan

Artefacto JSON declarativo producido por `cli_clickup.py` que el agente
aplica con `use-clickup`. Contiene `to_create` / `to_update` / `to_archive`
/ `unresolved`. NO se ejecuta directamente — el agente lo lee y orquesta.

_Evitar_: "clickup delta", "clickup patch", "task list"

## delta

Diferencia entre el estado actual de Moodle (fuente de verdad) y el
estado actual de ClickUp, expresada como `sync_plan`. Calculado por
`cli_clickup.py`; aplicado por el agente.

_Evitar_: "cambios pendientes", "diferencia", "patch list"

## agente-orquestador

Entidad (humano o AI agent) que decide cuando correr `cli_estado.py`,
`cli_calificaciones.py`, `cli_clickup.py` y `use-clickup`. No es un
script — es el policy layer.

_Evitar_: "el modelo", "el script", "el orquestador"

## direccion-de-flujo

Regla arquitectonica: datos fluyen Moodle → Local → ClickUp, nunca al
reves. Reclasificaciones van como `to_update` del mismo `task_id`;
eliminaciones de Moodle van como `to_archive`, NO `to_delete`.

_Evitar_: "sincronizacion bidireccional", "clickup como source", "reorganizar"
