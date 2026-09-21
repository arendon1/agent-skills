# REVIEW — PLAN JEV como herramienta nativa del harness Pi

**Autor**: Reviewer agent (glm) · **Fecha**: 2026-09-21 · **Veredicto**: CONDITIONAL-GO
**Método**: cada afirmación contrastada contra código real (extensiones, settings, READMEs), docs de pi 0.86.1, la constitución de agent-skills, directivas de seguridad, y RESEARCH.md.

---

## Hallazgos CRÍTICOS

### C1. Hosts de egreso nuevos sin announce-then-run (viola AGENTS.md)
El paso 3 hace una llamada real al Vercel AI Gateway, y B.5/B.3 añaden `api.typesafe.ai`. Ninguno está en la lista de egreso permitido de `~/.pi/agent/AGENTS.md` Tier 1 §3, y Tier 3 §14 exige announce-then-run para host nuevo. Máquina con EDR/NAC/DLP = riesgo laboral. **Fix**: añadir "nuevos hosts de egreso: X, Y — ¿autoriza?" a las decisiones de Andrés.

## Hallazgos MAYORES

### M1. Afirmación "verificada exhaustivamente" es FALSA
El plan afirma que `ext:web-search/web_search` no existe ("verificado con grep exhaustivo"). **Falso**: existe en `pi-extensions/extensions/web-search/index.ts:704-705` y está cargada (`settings.json:66`). La conclusión (referencia colgante → warning sin romper) sobrevive por el README de pi-subagents (378/385), pero el precedente citado no existe. **Fix**: re-anclar F.3/A.3 al README:378/385.

### M2. Activación sin la compuerta de calibración que el research declara obligatoria
RESEARCH §9 (severidad Alta): "POC obligatorio antes de promover cualquier workflow". El TL;DR ordena evaluar Laya en Fase 1 antes de integrar. El plan no tiene criterio de accuracy/calibración; el paso 4 expone la tool a TODOS los agentes con el claim central (calibración) sin validar una sola vez. **Fix**: condicionar activación/scoping al POC de Fase 1; marcar calibración como no-verificada en promptGuidelines.

### M3. Inconsistencia: prohíbe `Type.Union` y lo usa
A.1 dice no usar `Type.Union`; C.1 usa `Type.Union([Type.String(), Type.Record(...)])`. **Fix**: verificar schema contra el provider default, o restringir `state` a string.

### M4. Patrón de concurrencia mal citado
El plan cita "inFlight = 8, patrón antigravity-worker". Real: `MAX_CONCURRENT = 3` (`antigravity-worker/delegate.ts:24`) y **rechaza** en exceso con error, no encola. **Fix**: documentar la desviación (queue vs reject) o adoptar reject.

## Hallazgos MENORES

- M5. Budget: "$5 ≈ 117K llamadas a $0.000042" contradice RESEARCH §4.1 ("$0.0004/caso") → ~12.5K, no 117K.
- M6. Deriva de citas: Researcher.md línea 6 (no 7); cmux línea 13; `subs_first` routing.json:14; umbral 0.7 es §7.2-D (no §7.1-D).
- M7. README de model-router desactualizado (`index.ts` ya existe).
- M8. Fuente de `est_cost_usd` sin especificar (¿la API devuelve usage o estimamos?).

## Confirmaciones (verificado, resiste)

- Mecánica de pi 0.86.1 íntegra: autocarga, registerTool, promptSnippet/Guidelines, throw→isError, usage accounting, truncation, registerCommand, npm deps junto a extensión, registerProvider.
- `typebox/value` 1.3.30 exporta `Value.Check` (probado en vivo).
- Patrones de casa reales: PRESENT/ABSENT de cmux, ledger best-effort, `WorkerPi`, minimax.ts con fetchImpl inyectable, `providerQuota.*` con degradación, StringEnum.
- pi-subagents 0.19.0: scoping, warnings, `maxConcurrent:20`, `scopeModels:true`.
- Router blind-spot honesto (model-router solo intercepta Agent/SubagentWorkflow; JEV pasa libre — justificado contra RESEARCH §7.4).
- Precios del RESEARCH exactos.
- §9 agnosticismo respetado por reflexión (no toca agent-skills).
- Seguridad del resto: sin sudo, sin persistencia, key nunca en logs, rollback reversible, zero-diff en settings/models/routing.

## Veredicto

```
CRÍTICOS:  1  (C1 — egreso a hosts nuevos)
MAYORES:   4  (M1 evidencia falsa, M2 sin gate de calibración,
               M3 schema vs providers, M4 concurrencia mal citada)
MENORES:   4
gate: CONDITIONAL-GO
```

Diseño sólido, ~90% de las verificaciones resisten. No implementar tal cual. Correcciones necesarias antes de GO:
1. Añadir la decisión de hosts de egreso nuevos (C1).
2. Re-anclar el precedente de referencias colgantes (M1).
3. Condicionar activación/scoping al POC de Fase 1 (M2).
4. Verificar schema contra el provider default + documentar la desviación de concurrencia (M3/M4).

Con esas cuatro correcciones: **GO**.
