# Implementación — JEV/Laya como tool nativa del harness

**Fecha**: 2026-09-21 · **Estado**: ACTIVO · **Veredicto previo**: CONDITIONAL-GO → **GO**

El plan (`plan-jev-as-pi-tool.md`) fue revisado adversarialmente
(`review-jev-as-pi-tool.md`) con 1 crítico + 4 mayores. Esta es la implementación
con las cinco correcciones aplicadas.

## Dónde vive

```
~/.pi/agent/extensions/
├── jev/
│   ├── index.ts      ← la extensión (ACTIVO: su existencia es la activación)
│   ├── schema.ts     ← TypeBox + validación local + normalización + StringEnum local
│   ├── gateway.ts    ← 4 proveedores detrás de JevProvider + cola + errores HTTP
│   ├── config.ts     ← claves, política por preset, umbrales, presupuesto, hosts nuevos
│   ├── ledger.ts     ← JSONL append-only best-effort + stats
│   ├── demo.ts       ← corre todo sin pi
│   └── README.md
├── tests/jev.test.ts ← 35 tests
└── tsconfig.json     ← se agregó "jev/**/*.ts" al include
```

**NO versionado**: `~/.pi/agent` no es un repo git (verificado). La extensión vive
fuera de control de versiones, igual que las demás (`cmux`, `model-router`,
`provider-quota`). No se introdujo una convención nueva.

## Las cinco correcciones del review, aplicadas

| # | Corrección pedida | Cómo quedó |
|---|---|---|
| **C1** | Hosts de egreso nuevos sin announce-then-run | El default es **Laya local** (cero egreso). OpenRouter es el segundo (host ya autorizado). Vercel/TypeSafe solo se construyen con key explícita, y `/jev-stats` reporta `egreso NUEVO en uso`. |
| **M1** | Una afirmación "verificada exhaustivamente" era falsa | No se apoya nada en ella. El rollback son 2 líneas verificadas. |
| **M2** | Activación sin compuerta de calibración | `calibration_verified: false` en cada respuesta + el aviso en `description` (donde el modelo lo lee). Umbrales marcados PROVISIONAL. |
| **M3** | El schema usaba `Type.Union` pese a prohibirlo | `state` es `Type.String()`. |
| **M4** | Patrón de concurrencia mal citado | Cola con tope 4, **desviación documentada** de `antigravity-worker` (que rechaza). |

## Verificación (todo ejecutado, nada asumido)

```
npx tsc --noEmit                  -> exit 0
npm test                          -> 223 tests, 223 pass, 0 fail  (35 son de jev)
node --import tsx jev/demo.ts     -> política resuelta, sin gastar nada
node --import tsx jev/demo.ts --live -> llamada real a Laya
```

Salida del `--live` con Laya corriendo:

```
backend:   laya (local, sin egreso)
latencia:  344ms
costo:     $0.000000
score_at_max: 0.6137   all_answers_committed: 0.5817
con umbral de Laya (0.40) -> pass
```

Y la política resolviendo por preset:

```
slide_done_v1        laya✓ openrouter✓   -> laya (umbral 0.4)
ai_dimensions_v1     openrouter✓          -> openrouter (umbral 0.75)   # Laya excluida
```

## Bugs encontrados durante la implementación

| # | Bug | Causa | Fix |
|---|---|---|---|
| 1 | `tsconfig.include` no listaba `jev/` | El `tsc --noEmit` daba exit 0 sin haber chequeado NADA | Se agregó `jev/**/*.ts` |
| 2 | `PiLike extends ExtensionAPI` incompatible | Re-declaré `registerCommand` con firma distinta | `type PiLike = ExtensionAPI` |
| 3 | `@earendil-works/pi-ai` no resuelve | Vive ANIDADO dentro de `pi-coding-agent` | `StringEnum` copiado local (4 líneas verificadas) |
| 4 | `paths` en tsconfig rompió `tsx` | El loader tomaba el `.d.ts` como módulo | Se revirtió; el fix fue el #3 |
| 5 | El handler de comando devolvía `void` | pi exige `Promise<void>` | `async` |

**El #1 y el #3 son los que importan**: el primero habría dado un "type-check
verde" completamente falso; el segundo habría hecho fallar la extensión al cargar
dentro de pi, donde no hay forma de verlo hasta que rompe la sesión.

## Rollback

```bash
rm -rf ~/.pi/agent/extensions/jev
rm ~/.pi/agent/extensions/tests/jev.test.ts
# revertir "jev/**/*.ts" del include del tsconfig
```

Reiniciar pi. Nada persiste en sesiones: la tool no escribe estado; una sesión
vieja que la haya llamado muestra el resultado histórico sin poder re-ejecutarlo
(comportamiento estándar de pi ante tools removidas).

## Pendiente de Andrés

1. **Autorizar `ai-gateway.vercel.sh` / `api.typesafe.ai`** — solo si se quiere JEV
   contra el vendor. Hoy no hace falta: Laya local cubre lo mismo sin egreso.
2. **Calibrar los umbrales con etiquetas reales** (~200 casos) antes de confiar en
   algo con blast radius.
3. **Presupuesto mensual** (hoy $5, y solo aplica si se usa OpenRouter).