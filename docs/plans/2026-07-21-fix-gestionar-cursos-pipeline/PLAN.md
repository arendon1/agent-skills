# PLAN — fix(gestionar-cursos): modo plan-local + delta Moodle→ClickUp

## §T TASKS

```
id|status|task|cites
T0|[ ]|commit aislado de sync_calificaciones_clickup.py (cambio de 6d7fb79)|G,C5
T1|[ ]|_parse_porcentaje en scripts/_parsing.py, tolerante a 10+ formatos|V3,B1
T2|[ ]|fix main() de cli_calificaciones.py: persistir antes de imprimir, dry-run imprime|V4,B2
T3|[ ]|cli_clickup.py reescrito como plan-local: produce sync_plan.json, no toca API|V1,B3,B4
T4|[ ]|tests/ con conftest.py que mockea console de Rich y pre-pobla sys.path|V8,B7
T5|[ ]|test_parsing.py: 12+ casos de _parse_porcentaje|V3
T6|[ ]|test_cli_calificaciones.py: B1 (todos Pendiente) + B2 (orden persistencia)|V3,V4
T7|[ ]|test_cli_clickup_plan.py: produce sync_plan.json valido sin tocar la API|V1,V7
T8|[ ]|pyproject.toml: añadir pytest al array dev existente|V8,B6
T9|[ ]|SKILL.md refactor: mover secciones a references/, queda <= 450 lineas|V5 §15
T10|[ ]|references/sync-flow.md NUEVO: contrato agente/skill + delta + idempotencia|C1,C3,C4
T11|[ ]|references/folder-structure.md NUEVO: extraido de SKILL.md|T9
T12|[ ]|references/agents-md-template.md NUEVO: extraido de SKILL.md|T9
T13|[ ]|CONTEXT.md raiz: anadir terminos sync_plan, delta, agente-orquestador, direccion-de-flujo|C1
T14|[ ]|LESSONS.md: anadir L8 stale caches, L9 regla no-import, L10 clickup terminal|C5,C1,C4
T15|[ ]|validacion visual con browser: Moodle gradebook + ClickUp panel|C6
T16|[ ]|skill-forge audit gestionar-cursos: exit 0|V5
T17|[ ]|pytest exit 0 sobre toda la suite|V8
T18|[ ]|commit conventional con cuerpo explicando el cambio de modelo (a)|G
```

## §I INTERFACES (sketch, ratificado en PRD)

### `sync_plan.json` (NUEVO, producido por `cli_clickup.py`)

Ver PRD §I para el schema completo. Decisiones de diseño clave:

- `to_update.diff.status.from` → si no coincide al aplicar, agente aborta esa entrada.
- `comment` separado del `diff` → POST distinto a PUT, evita borrar el comentario.
- `_meta.schema_version` → para forward compatibility.
- `unresolved` → items que el plan no puede resolver; el agente los reporta al humano.

### `_parse_porcentaje` (NUEVO helper, en `scripts/_parsing.py`)

```python
def _parse_porcentaje(valor) -> float:
    """Parsea un valor de porcentaje del gradebook Moodle.
    Tolerante a None, "", "-", "—", "N/A", "Sin calificar", "100%", " - %",
    "12,5 %", "12.5 %", " 12,50 % ". Retorna float o 0.0 si no parseable.
    """
    if valor is None:
        return 0.0
    s = str(valor).strip()
    if not s or s in ("-", "—", "N/A", "Sin calificar"):
        return 0.0
    try:
        # Quitar % y normalizar coma decimal
        cleaned = s.replace("%", "").replace(",", ".").strip()
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0
```

Casos cubiertos (mínimo 12): `None`, `""`, `"-"`, `"—"`, `"N/A"`, `"Sin calificar"`,
`"0,00 %"`, `"12,50 %"`, `"100,00 %"`, `"100%"`, `" - %"`, `"12.5 %"`.

## §N IMPLEMENTATION NOTES

### T0 — Commit aislado de `sync_calificaciones_clickup.py`

```bash
git status  # confirmar modified
git diff domain/gestionar-cursos/scripts/sync_calificaciones_clickup.py
git add domain/gestionar-cursos/scripts/sync_calificaciones_clickup.py
git commit -m "chore(gestionar-cursos): preserve change to sync_calificaciones

Pre-fix cleanup. Este cambio del commit 6d7fb79 sobrevivia en working tree
sin commit. Aislarlo para que el fix del pipeline no se mezcle con el."
```

Por qué: el plan folder esta untracked Y `sync_calificaciones_clickup.py`
esta modified sin commitear. Sin T0 el `git add` del fix (T18) arrastra
cambios no auditados de otro trabajo.

### T1 — `_parse_porcentaje` en `scripts/_parsing.py`

Crear `domain/gestionar-cursos/scripts/_parsing.py` con la funcion
`_parse_porcentaje` descrita arriba. Módulo compartido para futuras
reglas de parsing (Moodle usa diferentes locales según la institucion).

### T2 — `cli_calificaciones.py:main()` reordenado

Diff objetivo:

```python
# ANTES (lineas 485-516 aprox):
items = _parsear_gradebook(html)
json.dump(items, f, ...)              # JSON escrito OK
_imprimir_resumen(items)               # CRASHEA aqui si todos Pendiente
if args.dry_run:
    return                             # tabla NUNCA se imprimio en dry-run
for item in items:
    _actualizar_md_actividad(...)      # NUNCA corre si tabla fallo
_actualizar_snapshot(...)              # NUNCA corre si tabla fallo

# DESPUÉS:
items = _parsear_gradebook(html)
json.dump(items, f, ...)
if not args.dry_run:                   # persistir SOLO si no es dry-run
    for item in items:
        _actualizar_md_actividad(...)
    _actualizar_snapshot(...)
try:
    _imprimir_resumen(items)           # imprimir SIEMPRE, aun en dry-run
except Exception as e:
    console.print(f"[yellow]⚠ Resumen no se pudo imprimir: {e}[/yellow]")
```

Clave: la persistencia se mueve DENTRO del `if not args.dry_run` (que ya
existia). El resumen se imprime siempre, envuelto en try/except.

### T3 — `cli_clickup.py` reescrito como plan-local

**Cambio arquitectonico:** el script deja de tocar la API de ClickUp.
Solo produce el delta.

```python
# ANTES (lineas 280-330):
client = get_client()  # NameError, ademas viola C1
folder_id = _resolver_folder(client, ...)
# ... mas llamadas que tampoco funcionan

# DESPUÉS:
plan = {
    "_meta": {
        "periodo": periodo,
        "generated_at": datetime.now().isoformat(),
        "source": "moodle",
        "schema_version": 1
    },
    "to_create": [],
    "to_update": [],
    "to_archive": [],
    "unresolved": []
}

# Resolver localmente (lee clickup.json, NO la API):
folder = clickup_data.get("folder", {}).get("id")
if not folder:
    plan["unresolved"].append({"item": "folder", "reason": "clickup.folder.id es null"})

# Comparar Moodle vs clickup.json local:
for curso in cursos:
    list_id = curso.get("list_id")
    if not list_id:
        plan["unresolved"].append({"item": curso["key"], "reason": "clickup.list_id es null"})
        continue
    for actividad in actividades_moodle:
        task_id = _match_task(actividad, curso.get("tasks", []))
        if not task_id:
            plan["to_create"].append(_build_create(actividad, list_id))
        elif _needs_update(actividad, curso["tasks"][task_id]):
            plan["to_update"].append(_build_update(actividad, curso["tasks"][task_id]))

# Escribir el plan:
with open(plan_path, "w") as f:
    json.dump(plan, f, indent=2, ensure_ascii=False)
```

**Cero imports de `use-clickup`.** Cero llamadas HTTP. Solo filesystem + JSON.

### T4 — `tests/conftest.py` con mocks de Rich

```python
# tests/conftest.py
import sys, os
from unittest.mock import MagicMock
import pytest

# Pre-poblar sys.path para que `import cli_calificaciones` funcione
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

@pytest.fixture(autouse=True)
def mock_rich_console(monkeypatch):
    """Mockear console de Rich para que los tests no fallen en CI sin TTY."""
    fake_console = MagicMock()
    fake_console.print = MagicMock()
    fake_console.log = MagicMock()
    monkeypatch.setattr("cli_calificaciones.console", fake_console)
    monkeypatch.setattr("cli_clickup.console", fake_console)
```

### T5, T6, T7 — Tests

T5 (`test_parsing.py`): tabla exhaustiva de los 12+ formatos listados en T1.
T6 (`test_cli_calificaciones.py`): reproduce el bug original (todos Pendiente)
y verifica que la persistencia corre ANTES del resumen, incluso en `--dry-run`.
T7 (`test_cli_clickup_plan.py`): corre `cli_clickup.py` con fixtures de
`snapshot.json` + `clickup.json` locales, verifica que el `sync_plan.json`
producido tiene la estructura correcta con `to_create`/`to_update`/`to_archive`
clasificados, sin hacer ninguna llamada HTTP (verificable con
`unittest.mock.patch("requests.get")` que NO se llama).

### T8 — `pyproject.toml`: añadir pytest al array existente

```bash
# ANTES (lineas 20-25):
[dependency-groups]
dev = ["rich>=13.0", "ruff>=0.5", "ty>=0.0.1a5"]

# DESPUÉS:
[dependency-groups]
dev = ["rich>=13.0", "ruff>=0.5", "ty>=0.0.1a5", "pytest>=8.0"]
```

NO duplicar el bloque `[dependency-groups]`. Solo añadir el item al array.

### T9 — SKILL.md refactor

Mover a `references/` (ver T11, T12) lo que no sea directiva operativa:
- "Heurísticas de Extracción" (5 lineas) → ya linkea a `references/extraccion-heuristicas.md`, eliminar de SKILL.md.
- "Formato de Fechas" (10 lineas) → consolidar en `references/fechas-fuente-de-verdad.md`.
- "Estructura de Carpetas Local" (40 lineas) → `references/folder-structure.md`.
- "AGENTS.md - Contenido" (35 lineas) → `references/agents-md-template.md`.
- Sub-flujo `foros` (30 lineas) → comprimir a 5 lineas + link.

SKILL.md queda en ~440 lineas, suficiente para anadir bloque "Contrato
agente/skill" (~30 lineas) sin pasarse de 500.

### T10 — `references/sync-flow.md` (NUEVO)

Documento clave del fix. Contiene:

1. **Contrato agente/skill**: diagrama del flujo Moodle→Local→ClickUp con
   flechas explicitas.
2. **Schema de `sync_plan.json`**: copy-paste del PRD §I con anotaciones
   sobre cada campo.
3. **Idempotencia**: tabla de "que pasa si re-corro N veces" para cada modo.
4. **Casos degenerados**: Moodle caido, ClickUp caido, curso no inicializado,
   actividad renombrada, actividad eliminada, plan con todos los items
   `unresolved`.
5. **Quirk conocido**: `status_id` vs `status name` (la leccion 2026-2-B1
   del script viejo, preservada aqui).

### T13 — `CONTEXT.md` raiz (NUEVO)

```markdown
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
```

### T14 — `LESSONS.md`: 3 lecciones nuevas

- **L8 (stale caches):** caches locales (`calificaciones.json`, `snapshot.json`,
  `clickup.json`) pueden tener horas o dias de antiguedad. El plan no debe
  asumir que el `calificacion` que ve es el actual. El agente decide cuando
  re-sincronizar; el script solo reporta `_meta.stale_at` si la cache tiene >24h.
- **L9 (regla no-import entre skills):** el hecho de que un skill de dominio
  USE a otro no significa que deba importarlo. `use-clickup` es una API que
  el agente invoca, no una libreria que el skill linkea. Imports cruzados
  rompen la regla de composicion y hacen los skills no-desplegables
  independientemente.
- **L10 (ClickUp terminal):** ClickUp no se reorganiza desde codigo. Renombres,
  reclasificaciones, eliminaciones fisicas son operaciones manuales. El
  script planifica cambios, no los ejecuta. El humano es el owner de la
  estructura de su workspace.

### T15 — Validacion visual con browser

Disciplina, no codigo. Antes de marcar T17 (pytest) como done:

1. Lanzar Chrome con `--remote-debugging-port=9222` (ya lo hace `navegador_cdp.py`).
2. Conectar via CDP y navegar al gradebook del curso de prueba.
3. Capturar screenshot del gradebook con todos los items en "Pendiente" — confirma
   que `_parse_porcentaje` cubre los formatos reales.
4. Correr `cli_calificaciones.py --dry-run` y verificar que la salida en consola
   es la esperada.
5. Para ClickUp: abrir el panel real en el browser, comparar con el `sync_plan.json`
   producido. Verificar que los `task_id`, `list_id`, `status`, `tags` que el
   plan dice son los mismos que ClickUp muestra.

Si la validación visual revela formatos no cubiertos, iterar sobre T1.

## §V VERIFICATION (post-build)

```bash
cd /Users/andres.rendon/Documents/Projects/agent-skills
uv sync --project domain/gestionar-cursos --dev
cd domain/gestionar-cursos

# Unit tests
uv run pytest -v
# → exit 0 (D6)

# Audit
uv run python ../../utility/skill-forge/scripts/audit.py gestionar-cursos
# → exit 0 (D7)

# Manual end-to-end
cd /Users/andres.rendon/Documents/Universidad/2026-2-B1
uv run --project ~/.agents/skills/gestionar-cursos \
  python ~/.agents/skills/gestionar-cursos/scripts/cli_calificaciones.py \
  "2607B04G1-lenguaje-de-programación-avanzado-1"
# → exit 0 (D1)
# → snapshot.json tiene calificacion por cada actividad (D2)
# → archivos .md tienen ## Calificacion (D3)

uv run --project ~/.agents/skills/gestionar-cursos \
  python ~/.agents/skills/gestionar-cursos/scripts/cli_clickup.py .
# → exit 0 (D4)
# → clickup.json tiene _meta + sync_plan con las 4 secciones (D5)
# → cero requests HTTP a api.clickup.com
```

**Deploy (FUERA de este plan, post-merge):**
```bash
skills add arendon1/agent-skills -a hermes-agent -g -y --skill gestionar-cursos
```

## §R REFS

- PRD.md — requirements
- LESSONS.md — lecciones (existentes L1-L7 + nuevas L8-L10)
- AGENTS.md raiz — constitucion (§3, §9, §11, §15)
- use-clickup/scripts/client.py — API consumida por el agente
- /tmp/agy_review_prompt.md — transcript del adversarial review
- /Users/andres.rendon/.hermes/cache/delegation/live/deleg_fe8dd1fd/ — transcript del subagent review
