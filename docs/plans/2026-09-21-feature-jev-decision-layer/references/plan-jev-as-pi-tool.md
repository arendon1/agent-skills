# PLAN — JEV como herramienta nativa del harness Pi

**Autor**: Planner agent (glm) · **Fecha**: 2026-09-21 · **Estado**: revisado, CONDITIONAL-GO
**Alcance**: investigación de viabilidad + diseño. Sin implementación.

Corrección de premisa: las extensiones de este harness viven en `~/.pi/agent/extensions/` (global), NO en `.pi/extensions/` (vacío).

---

## FASE A — Mapeo del harness actual

- Descubrimiento: pi auto-carga `~/.pi/agent/extensions/*.ts` y `*/index.ts`; `.pi/extensions/` (proyecto); `settings.json` → `packages`.
- Registro de tool: `pi.registerTool({ name, label, description, promptSnippet, promptGuidelines, parameters (typebox), execute, renderCall, renderResult })`.
  - `promptSnippet` = línea en "Available tools" (descubrimiento sin leer código).
  - `promptGuidelines` = bullets que DEBEN nombrar la tool.
  - Enums: usar `StringEnum` de `@earendil-works/pi-ai` (no `Type.Union`/`Type.Literal`).
  - Errores: `throw` → `isError: true`, sesión continúa; retornar nunca marca error.
- Patrón staged de la casa: desarrollar sin entry-point, activar creando `index.ts`.
- No hay cliente HTTP unificado; cada extensión resuelve el suyo (patrón `provider-quota/providers/minimax.ts` con `fetchImpl` inyectable, timeouts, errores tipados).

## FASE B — Diseño

- **Decisión**: tool nativa vía `pi.registerTool`, NO `pi.registerProvider` (JEV no es modelo de chat; registrarlo como provider corrompería el sistema de modelos y su política de vetos — RESEARCH §7.4 ya lo descartó).
- Estructura (patrón model-router): `index.ts` (staging), `schema.ts`, `gateway.ts` (seam `JevProvider`), `config.ts`, `ledger.ts`, `demo.ts`, tests.
- Credenciales: `VERCEL_AI_GATEWAY_API_KEY` → `TYPESAFE_API_KEY` (lectura en execute-time). Opcional bloque `jev` en `auth.json`. Nunca loggear la key.
- Sin key: tool SIEMPRE registrada; descripción refleja estado; `throw JEV_NO_KEY` en execute (no crash). NO auto-fallback a LLM dentro de la tool.
- Routing: siempre JEV dentro de su nicho (es el más barato del nicho). Cascada vive arriba (orquestador aplica umbral).
- Seam Laya (`JevProvider`) desde día 1, implementación diferida.

## FASE C — Schemas

- Input TypeBox: `state` (string|record), `questions` (Record de {type, instructions, options?, scale?}), `provider?`, `timeoutMs?`. `maxItems: 255` para Choice.
- Validación local con `Value.Check` (`typebox/value`) antes de la API.
- Output normalizado: `{ok, answers: {key: {type, value, probability}}, meta: {provider, latency_ms, est_cost_usd, request_id, retries}}`. Probabilidad fuera de [0,1] → `JEV_MALFORMED` (no clamp).

## FASE D — Operación

- Descubrimiento vía `promptSnippet` + `promptGuidelines` (batch: "put ALL questions in a single call"; umbral sugerido 0.7).
- Taxonomía de errores: `JEV_NO_KEY`, `JEV_AUTH`, `JEV_RATE_LIMIT`, `JEV_UPSTREAM`, `JEV_TIMEOUT`, `JEV_MALFORMED`, `JEV_BUDGET`, `JEV_SCHEMA`.
- Ledger `~/.pi/agent/logs/jev.jsonl` append-only best-effort. `/jev-stats` command.
- Costo: lo absorbe la cuenta dueña de la key. Budget cap propuesto $5/mes fail-closed.

## FASE E — Riesgos

Vendor lock-in (media, seam + Gateway sin contrato), key leak (alta, key nunca en logs), calibración no verificada (alta, tool reporta probability cruda; consumidor aplica umbral), rate bursts (baja, cap inFlight + 1 retry), timeout (baja, 10s vs 200-300ms típico), dispersión de preguntas (media, promptGuidelines batch), hype scope creep (media, no auto-promoción).

## FASE F — Implementación

Orden: (1) schemas+validación, (2) clientes HTTP+seam+config+ledger, (3) probe real fuera de pi + verificar wire-format del Gateway (incógnita mayor), (4) ACTIVACIÓN (crear `index.ts`, reiniciar pi), (5) verificación e2e, (6) scoping opcional de subagentes, (7) governance opcional.

Criterios de éxito: `/jev-stats` responde; probe con probability ∈ (0,1); batch de 5 preguntas = 1 línea de ledger; sin key → `JEV_NO_KEY` sin crash; budget → `JEV_BUDGET`; subagente la ve si tiene `ext:jev/jev`; suite de tests + tsc limpios; **zero diff** en settings/models/routing y en agent-skills.

Rollback: `rm -rf ~/.pi/agent/extensions/jev` + revert frontmatter + reiniciar pi.

Incógnita principal: wire-format del Vercel AI Gateway para cliente HTTP crudo (RESEARCH documenta `experimental_evaluate`, no el body nativo). Plan B: usar el paquete `ai` como dep npm.

### Lo que NO recomienda
1. NO registrar en `models.json`/`registerProvider`.
2. NO tocar `routing.json`/`enabledModels`.
3. NO auto-fallback a m3/glm dentro de la tool.
4. NO crear skill en agent-skills (viola §9 en espíritu).
5. NO depender de la waitlist TypeSafe (Gateway primario).
6. NO exponer a agentes con permisos de mutación sin gates.

## Decisiones pendientes de Andrés

1. Nombre: `jev` vs `evaluate` (recomienda `jev`).
2. Key: env vs bloque auth.json (recomienda env primario + auth.json fallback).
3. Budget mensual (propone $5/mes) y quién absorbe el gasto.
4. Wire-format Gateway: ¿acepta dep npm `ai` si el Gateway solo expone `experimental_evaluate`?
5. Scoping inicial: default-all + observar 2 semanas (recomendado) vs lista explícita.
6. `/jev-stats` propio vs fold en `/quota` (recomienda propio).
7. Umbral por defecto 0.7: ¿política de casa o por-consumidor?
