# ARD: skill de reporte de compensación

**Plan:** `2026-07-11-feature-compensation-report-skill`
**Estado:** ✅ implementado

## Decisión arquitectónica

Skill único, autocontenido, sin dependencias runtime de otros skills
del repo. Vive en `domain/compensation-report/` porque:

- Es un loop con deliverable concreto (un archivo markdown) → capa
  `domain` por convención del repo (ver AGENTS.md §3, §4).
- No orquesta otros loops del SDD pipeline (`grill`, `plan`, `build`)
  → no es `process`.
- No es leaf de soporte (no lo invocan otros skills) → no es `utility`.

## Capas e interfaces

```
+-------------------------+
| Usuario (humano)        |
| "necesito un reporte"   |
+----------+--------------+
           |
           v
+-------------------------+
| compensation-report     |  ← skill de loop, invocation: user
| (domain)                |
+----------+--------------+
           |
           v
+-------------------------+
| Investigación externa   |  ← búsqueda web, extracción de páginas
| (web search/extract)    |
+-------------------------+
           |
           v
+-------------------------+
| Triangulación + cálculo |  ← en memoria del agente
+-------------------------+
           |
           v
+-------------------------+
| Reporte markdown        |  ← archivo escrito al home
+-------------------------+
```

## Capas (Layer 2 domain, AGENTS.md §3)

| Capa | Skill que se invoca | Razón |
|---|---|---|
| L3 utility | ninguno en este flujo | No requiere caveman ni bootstrap |
| L2 domain | ninguno en este flujo | No consume use-clickup, make-a-diagram, etc. |
| L1 process | nunca | Por regla §3, domain MUST NOT invocar process |

## Interfaces de entrada

| Nombre | Tipo | Requerido | Notas |
|---|---|---|---|
| `cargo` | string[] | sí | uno o varios cargos objetivo |
| `experiencia_anos` | number | sí | años de experiencia total |
| `ubicacion` | string | sí | ciudad/país + modalidad |
| `empresa_objetivo` | string | sí | nombre o "mercado general" |
| `stack` | string[] | no | herramientas o skills destacadas |
| `salario_actual` | number | no | para calcular delta |
| `tipo_contratacion` | enum | no | default: empleado_directo |
| `moneda` | enum | no | default: ambas |
| `ciudades` | string[] | no | default: país completo |
| `nivel` | enum | no | default: inferido por años |
| `sector` | string | no | default: mercado general |
| `beneficios_actuales` | string[] | no | default: beneficios típicos |

## Interface de salida

Un único archivo markdown con:

- 7 secciones obligatorias en orden fijo
- Tablas salariales siempre con 4 columnas: USD/año, USD/mes, COP/año,
  COP/mes
- ≥ 3 fuentes por percentil publicado
- ≥ 10 fuentes totales citadas entre §2, §3 y §7
- Header con TRM y fecha
- Advertencias accionables, no genéricas

## Datos persistentes

Ninguno. El skill no escribe bases de datos, no mantiene caché, no
genera logs. El reporte es el único artefacto.

## Riesgos arquitectónicos

- **Acoplamiento a las herramientas de búsqueda del adaptador.** El
  skill describe comportamiento ("investigar fuentes") sin nombrar la
  herramienta. El adaptador Layer 4 decide si usa `web_search`,
  `WebFetch`, `Brave Search` u otra. Razón: AGENTS.md §9 (agnosticismo).
- **Variabilidad de TRM entre fuentes.** Distintas APIs devuelven TRM
  ligeramente distintas. Mitigación: el skill exige una sola TRM por
  reporte, registrada al inicio, capturada del mismo hilo de
  investigación.
- **Falta de fuentes para roles emergentes** (ej. "Analytics Manager"
  en Latam es un cargo nuevo). Mitigación: si no hay ≥ 3 fuentes, se
  reduce a mercado general y se advierte.

## Cambios necesarios en otros archivos

- `domain/compensation-report/SKILL.md` (nuevo, 307 líneas, < 500 ✓)
- `docs/plans/2026-07-11-feature-compensation-report-skill/` (nuevo,
  este plan)
- `manifest.py` regenera automáticamente al correr `skill-forge`.

## Decisiones rechazadas

- **Skill como utility (no domain).** Rechazado: tiene deliverable
  concreto, no es soporte de otros skills.
- **Subdividir en 2 skills (interview + research).** Rechazado: la
  entrevista es trivial (12 campos) y dividir añade ceremonia sin valor
  (§11 right-size).
- **Output en HTML además de markdown.** Rechazado: AGENTS.md §6 dice
  "artifacts are markdown, HTML only when the user asks ad-hoc".
