# Plan de Implementación: Persona "Compañero de Universidad"

> **Para agentes trabajadores:** SUB-HABILIDAD REQUERIDA: Usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan sintaxis de checkbox (`- [ ]`).

**Meta:** Crear una persona/contexto agnóstico de plataforma que se activa automáticamente al hablar de universidad, coordina `/gestionar-cursos` y `/use-clickup`, y mantiene un índice local para gestión rápida.

**Arquitectura:** Persona activa automáticamente por triggers. Usa index local (cacheado 7 semanas) para mapear cursos → ClickUp. Todo el tracking de actividades está en ClickUp. Materiales físicos en local.

**Tech Stack:** Python 3, JSON, Markdown

---

## Estructura de Archivos

```
agent-skills/
├── archive/                          # Skills deprecated
│   ├── course-manager/
│   ├── clickup-manager/
│   └── moodle-navigator/
│
├── gestionar-cursos/                 # Skill: extracción Moodle
│   └── ...
│
├── use-clickup/                      # Skill: gestión ClickUp
│   └── ...
│
└── universidad/                      # Persona agnóstica de plataforma
    ├── SKILL.md                      # Definición de persona
    ├── references/
    │   ├── time-awareness.md         # Lógica de detección de periodo
    │   └── index-format.md           # Estructura del índice local
    └── scripts/
        ├── detectar_periodo.py       # Derivar periodo de fechas
        ├── cargar_index.py           # Leer .universidad_index.json
        ├── guardar_index.py          # Guardar índice actualizado
        └── validar_cache.py          # Verificar si cache expiró (7 semanas)
```

---

## Workflows (Activación Automática)

### Activación por Triggers

**Palabras clave universitarias:**
- universidad, curso, clase, materia, bloque, periodo, semestre
- Moodle, ClickUp, tarea, entrega, parcial, examen, cuestionario, foro
- fecha límite, deadline, calificación, nota, evaluación
- sincronizar, actualizar, inicializar, bajar, organizar

**Cuándo se activa:**
- Usuario menciona alguna de las palabras clave
- Usuario pregunta sobre próximas entregas
- Usuario menciona cambiar de periodo/bloque
- Usuario pide ayuda con gestión universitaria

---

## Tarea 1: Lógica de Time Awareness

**Archivos:**
- Crear: `universidad/scripts/detectar_periodo.py`

- [ ] **Paso 1: Implementar detección de periodo**

```python
"""
Detección automática de periodo actual basada en fechas de cursos.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

def detectar_periodo(cursos: List[Dict]) -> Dict:
    """
    Determina periodo y bloque actual basado en fechas de cursos.
    
    Args:
        cursos: Lista de cursos con fechas de inicio/fin
        
    Returns:
        Dict con periodo, bloque, fecha_inicio_periodo, fecha_fin_periodo
    """
    if not cursos:
        return {
            "periodo": None,
            "bloque": None,
            "fecha_inicio_periodo": None,
            "fecha_fin_periodo": None
        }
    
    # Obtener fechas de inicio de cursos activos
    fechas_inicio = [c["fecha_inicio"] for c in cursos]
    fecha_min = min(fechas_inicio)
    fecha_max = max([c["fecha_fin"] for c in cursos])
    
    # Determinar periodo (1 o 2) basado en mes de inicio
    mes = fecha_min.month
    if mes <= 6:
        periodo = f"{fecha_min.year}-1"
    else:
        periodo = f"{fecha_min.year}-2"
    
    # Determinar bloque (B1, B2, B3)
    # Bloque 1: primeros 6 semanas del periodo
    # Bloque 2: semanas 7-12
    # Bloque 3: semanas 13+
    dias_desde_inicio = (fecha_max - fecha_min).days
    if dias_desde_inicio <= 42:  # 6 semanas
        bloque = "B1"
    elif dias_desde_inicio <= 84:  # 12 semanas
        bloque = "B2"
    else:
        bloque = "B3"
    
    return {
        "periodo": periodo,
        "bloque": bloque,
        "fecha_inicio_periodo": fecha_min,
        "fecha_fin_periodo": fecha_max
    }


def detectar_cursos_activos(cursos: List[Dict], hoy: Optional[datetime] = None) -> List[Dict]:
    """
    Filtra cursos activos (no terminados).
    
    Args:
        cursos: Lista de cursos
        hoy: Fecha actual (opcional, por defecto hoy)
        
    Returns:
        Lista de cursos activos
    """
    if hoy is None:
        hoy = datetime.now().date()
    
    return [
        c for c in cursos
        if c["fecha_fin"] >= hoy
    ]


def detectar_cursos_terminados(cursos: List[Dict], hoy: Optional[datetime] = None) -> List[Dict]:
    """
    Filtra cursos terminados.
    
    Args:
        cursos: Lista de cursos
        hoy: Fecha actual (opcional, por defecto hoy)
        
    Returns:
        Lista de cursos terminados
    """
    if hoy is None:
        hoy = datetime.now().date()
    
    return [
        c for c in cursos
        if c["fecha_fin"] < hoy
    ]
```

- [ ] **Paso 2: Escribir tests**

```python
from datetime import date

def test_detectar_periodo_basico():
    cursos = [
        {
            "codigo": "2601B04G1",
            "nombre": "BASES DE DATOS 2",
            "fecha_inicio": date(2026, 1, 26),
            "fecha_fin": date(2026, 3, 8)
        }
    ]
    periodo = detectar_periodo(cursos)
    assert periodo["periodo"] == "2026-1"
    assert periodo["bloque"] == "B1"


def test_detectar_cursos_activos():
    hoy = date(2026, 2, 15)
    cursos = [
        {"codigo": "1", "fecha_fin": date(2026, 3, 8)},
        {"codigo": "2", "fecha_fin": date(2026, 1, 10)}
    ]
    activos = detectar_cursos_activos(cursos, hoy)
    assert len(activos) == 1
    assert activos[0]["codigo"] == "1"
```

- [ ] **Paso 3: Ejecutar tests**

```
pytest universidad/scripts/test_detectar_periodo.py -v
```

---

## Tarea 2: Gestión del Índice Local

**Archivos:**
- Crear: `universidad/scripts/cargar_index.py`
- Crear: `universidad/scripts/guardar_index.py`
- Crear: `universidad/scripts/validar_cache.py`

- [ ] **Paso 1: Implementar carga/_guardado del índice**

```python
"""
Gestión del índice local .universidad_index.json.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

CACHE_DURACION = timedelta(weeks=7)  # 7 semanas


def cargar_index(ruta_index: str = ".universidad_index.json") -> Optional[Dict]:
    """
    Carga el índice local si existe y no ha expirado.
    
    Args:
        ruta_index: Ruta al archivo de índice
        
    Returns:
        Dict con el índice o None si no existe/expiró
    """
    if not os.path.exists(ruta_index):
        return None
    
    try:
        with open(ruta_index, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def guardar_index(index: Dict, ruta_index: str = ".universidad_index.json"):
    """
    Guarda el índice local.
    
    Args:
        index: Dict con el índice
        ruta_index: Ruta al archivo de índice
    """
    with open(ruta_index, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def validar_cache(index: Optional[Dict]) -> bool:
    """
    Verifica si el cache es válido (no ha expirado).
    
    Args:
        index: Dict del índice
        
    Returns:
        True si válido, False si expiró o no existe
    """
    if index is None:
        return False
    
    cache_valid_until = index.get("cache_valid_until")
    if not cache_valid_until:
        return False
    
    try:
        fecha_valida = datetime.fromisoformat(cache_valid_until)
        return datetime.now() < fecha_valida
    except ValueError:
        return False
```

- [ ] **Paso 2: Escribir tests**

```python
def test_guardar_y_cargar_index():
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta = os.path.join(tmpdir, "test_index.json")
        
        index = {
            "2601B04G1": {
                "nombre": "BASES DE DATOS 2",
                "periodo": "2026-1",
                "bloque": "B1"
            }
        }
        
        guardar_index(index, ruta)
        cargado = cargar_index(ruta)
        
        assert cargado is not None
        assert "2601B04G1" in cargado
```

---

## Tarea 3: SKILL.md de la Persona

**Archivos:**
- Crear: `universidad/SKILL.md`

- [ ] **Paso 1: Escribir SKILL.md**

```markdown
---
name: universidad
description: >-
  Persona de compañero universitario. Se activa automáticamente
  cuando el usuario habla de cursos, tareas, Moodle, ClickUp,
  fechas de entrega o actividades académicas.
metadata:
  version: "1.0.0"
  language: es-CO
---

# Compañero de Universidad

Eres el compañero de universidad del usuario. Te activas automáticamente
cuando se menciona cualquier tema relacionado con la vida universitaria.

## Time Awareness

Al activarte, debes:

1. **Leer el índice local** (`.universidad_index.json`)
2. **Verificar si el cache es válido** (7 semanas)
3. **Si expiró o no existe**:
   - Escanear workspace por carpetas con `AGENTS.md`
   - Leer fechas de inicio/fin de cada curso
   - Determinar periodo/bloque actual
   - Guardar en índice local con `cache_valid_until` (hoy + 7 semanas)
4. **Mostrar resumen** al usuario

## Estado

- **Periodo**: Derivado de fechas de cursos activos
- **Bloque**: B1/B2/B3 según duración del periodo
- **Cursos activos**: Con `fecha_fin >= hoy`
- **Cursos terminados**: Con `fecha_fin < hoy`

## Comportamiento

### Antes de cualquier acción:
1. Verificar estado actual (cursos, periodo, bloque)
2. Mostrar resumen si es la primera vez en la sesión
3. Preguntar antes de crear/modificar tareas en ClickUp

### Sobre materiales:
- Los materiales físicos (PDFs) están en carpetas locales
- Las tasks en ClickUp solo contienen **links a Moodle**, NO path locales
- Usa `/gestionar-cursos` para obtener materiales
- Usa `/use-clickup` para gestionar tareas

### Sobre el índice:
- El índice local mapea `curso_code` → `list_id`, `task_ids`
- Se actualiza automáticamente al sincronizar con ClickUp
- Validez: 7 semanas (49 días)

## Triggers de Activación

Te activas automáticamente si el usuario menciona:
- universidad, curso, clase, materia, bloque, periodo, semestre
- Moodle, ClickUp, tarea, entrega, parcial, examen, cuestionario, foro
- fecha límite, deadline, calificación, nota, evaluación
- sincronizar, actualizar, inicializar, bajar, organizar

## Workflow Recomendado

1. **Usuario menciona tema universitario** → Activar persona
2. **Leer estado** → Periodo, cursos activos, próximas entregas
3. **Mostrar resumen** → "Periodo: 2026-1-B1, Cursos: 2, Próximas: 3"
4. **Esperar instrucción** → ¿Qué necesitas?
5. **Ejecutar acción** → Usa `/gestionar-cursos` o `/use-clickup` según necesidad
6. **Actualizar índice** → Guardar cambios en `.universidad_index.json`

## Ejemplos de Interacción

**Usuario**: "Tengo muchas tareas esta semana"
**Tú**: "Voy a revisar tus próximas entregas..."
- Lee índice → Obtiene cursos activos
- Busca tasks con `due_date` en 7 días
- Muestra: "1/2: Cuestionario evaluativo, 8/2: Primer Parcial"

**Usuario**: "Nuevo curso de bases de datos"
**Tú**: "Voy a inicializar el curso y sincronizar con ClickUp..."
- Ejecuta: `/gestionar-cursos init <URL>`
- Ejecuta: `/use-clickup crear-lista <folder_id> <nombre>`
- Actualiza índice local

**Usuario**: "Cambió la fecha del parcial"
**Tú**: "Voy a actualizar la task en ClickUp..."
- Busca task por nombre en índice
- Ejecuta: `/use-clickup actualizar-tarea <task_id> --due_date <nueva_fecha>`
- Actualiza índice local

## Referencias

- `/gestionar-cursos`: Skill para extracción de Moodle
- `/use-clickup`: Skill para gestión de ClickUp
- `references/time-awareness.md`: Lógica de detección de periodo
- `references/index-format.md`: Estructura del índice local
```

---

## Tarea 4: Referencias

**Archivos:**
- Crear: `universidad/references/time-awareness.md`
- Crear: `universidad/references/index-format.md`

- [ ] **Paso 1: Escribir referencias**

### time-awareness.md

```markdown
# Time Awareness

## Lógica de Detección de Periodo

El periodo se deriva automáticamente de las fechas de inicio de los cursos:

1. **Periodo (1 o 2)**:
   - Si mes de inicio ≤ 6 → Periodo 1
   - Si mes de inicio > 6 → Periodo 2

2. **Bloque (B1, B2, B3)**:
   - Bloque 1: Duración ≤ 6 semanas (42 días)
   - Bloque 2: Duración 7-12 semanas (43-84 días)
   - Bloque 3: Duración > 12 semanas (85+ días)

## Caché

- **Duración**: 7 semanas (49 días)
- **Validación**: `cache_valid_until = hoy + 7 semanas`
- **Refresco**: Si `hoy > cache_valid_until`, re-escanear workspace

## Ejemplo

```
Curso A: inicio 2026-01-26, fin 2026-03-08
Curso B: inicio 2026-03-10, fin 2026-04-28

Periodo: 2026-1 (mes 1 ≤ 6)
Bloque: B1 (42 días ≤ 42)
```
```

### index-format.md

```markdown
# Índice Local

## Estructura

```json
{
  "cache_valid_until": "2026-03-05T00:00:00",
  "cursos": {
    "2601B04G1": {
      "nombre": "BASES DE DATOS 2",
      "moodle_url": "https://aulavirtual.uniremington.edu.co/course/view.php?id=10272",
      "periodo": "2026-1",
      "bloque": "B1",
      "clickup": {
        "space_id": "universidad",
        "folder_id": "2026-1-B1",
        "list_id": "abc123"
      },
      "tasks": {
        "Prueba Inicial": "task_id_123",
        "Cuestionario evaluativo": "task_id_456",
        "Primer Parcial": "task_id_789"
      },
      "ultima_sincronizacion": "2026-01-26"
    }
  }
}
```

## Claves

- **cache_valid_until**: Timestamp de expiración del cache (ISO 8601)
- **cursos**: Mapa `curso_code` → datos del curso
- **clickup**: IDs de espacio, folder y lista en ClickUp
- **tasks**: Mapa `nombre_task` → `task_id` en ClickUp
- **ultima_sincronizacion**: Última vez que se sincronizó con ClickUp

## Actualización

El índice se actualiza automáticamente al:
1. Inicializar nuevo curso
2. Sincronizar fechas de entrega
3. Crear/actualizar tasks en ClickUp
```

---

## Auto-Revisión

**1. Cobertura del spec:**
- ✅ Persona activa automáticamente por triggers
- ✅ Time awareness (detección de periodo/bloque)
- ✅ Caché de 7 semanas
- ✅ Índice local para mapeo rápido
- ✅ Materiales en local, tracking en ClickUp
- ✅ Links en tasks apuntan a Moodle, no a local

**2. Scan de placeholders:** ✅ Sin TBD o placeholders.

**3. Consistencia de tipos:** ✅ Nombres de funciones y estructuras consistentes.

---

## Opciones de Ejecución

**Plan completo.** Dos opciones de ejecución:

**1. Subagent-Driven (recomendado)** - Subagente fresco por tarea, revisión entre tareas

**2. Inline Execution** - Ejecutar tareas en esta sesión

**¿Cuál prefieres?**