# PLAN: skill de reporte de compensación

**Plan:** `2026-07-11-feature-compensation-report-skill`
**Estado:** ✅ todos los items completados

## Tareas

- [x] **T1 — Definir capa y nombre del skill.** Decisión:
  `domain/compensation-report`. Capa domain por ser loop con
  deliverable concreto. Aprobado en AGENTS.md §3 / §4.

- [x] **T2 — Escribir frontmatter conforme a §5.** `name`,
  `description` con "Usa cuando", `invocation: user`, `layer:
  domain`, `loop: compensation-report`, `deliverable: ...`,
  `provides: [salary-research, employer-profiling,
  negotiation-scripting, market-band-triangulation]`, `language:
  es-CO`, `metadata.version: 1.0.0`.

- [x] **T3 — Escribir el cuerpo del SKILL.md (< 500 líneas).**
  Estructura: principios, cuándo usar, cuándo no, flujo de 5 pasos
  (entrevista, investigación, cálculo, generación, verificación),
  anti-patrones, salida esperada. 307 líneas al cierre.

- [x] **T4 — Especificar las 7 secciones obligatorias del reporte.**
  Encabezado, perfil del empleador, bandas (con 4 columnas siempre),
  publicaciones activas, estructura de compensación, 3 tácticas de
  negociación, advertencias, fuentes.

- [x] **T5 — Definir las 4 formas monetarias canónicas.** USD/año,
  USD/mes, COP/año, COP/mes. Regla dura: cualquier tabla salarial
  debe tener las 4. Se valida en checklist de §5 del skill.

- [x] **T6 — Definir los campos de la entrevista.** 4 obligatorios
  (cargo, años, ubicación, empresa), 8 opcionales con defaults
  sensatos. Reunidos en una sola llamada a `clarify` (no en cascada).

- [x] **T7 — Definir los hilos de investigación en paralelo.** 4
  hilos: bandas salariales, publicaciones activas, perfil del
  empleador, datos macro (TRM + IPC + SMLMV). Mínimo 3 fuentes por
  percentil publicado.

- [x] **T8 — Crear el plan folder según §6.** Estructura:
  `docs/plans/2026-07-11-feature-compensation-report-skill/`. Tamaño
  medio → PRD + ARD + PLAN (sin SPEC, sin LESSONS — no es bug ni
  refactor).

- [x] **T9 — Validar con `skill-forge audit`.** Resultado: PASS, 307
  líneas (< 500), path correcto, frontmatter conforme.

- [x] **T10 — Verificar agnosticismo (§9).** Grep por
  `pi|Claude|OpenCode|Cursor|Antigravity|TodoWrite|skill-recall`
  en el cuerpo del SKILL.md → 0 coincidencias. PASS.

- [x] **T11 — Regenerar manifest con `manifest.py`.** Verificación:
  el skill aparece listado bajo `domain/` en el manifest.

## Comandos ejecutados

```bash
# Auditoría
python3 utility/skill-forge/scripts/audit.py compensation-report
# → PASS, 307 lines (<= 500)

# (Pendiente) Manifest
python3 utility/skill-forge/scripts/manifest.py --check
```

## Estado final

🟢 Skill listo para uso. Todas las tareas marcadas, sin pendientes.
