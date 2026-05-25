# Plan de Implementación: Refactorización de Skills Universitarios

> **Para agentes trabajadores:** SUB-HABILIDAD REQUERIDA: Usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan sintaxis de checkbox (`- [ ]`).

**Meta:** Refactorizar completamente las skills de gestión universitaria con nueva arquitectura agnóstica de plataforma.

**Arquitectura:** Persona "Compañero de Universidad" activa automáticamente por triggers. Usa `/gestionar-cursos` para materiales y `/use-clickup` para tracking. Index local mapea cursos → ClickUp.

**Tech Stack:** Python 3, JSON, Markdown

---

## Estructura Final

```
agent-skills/
├── archive/                          # Skills deprecated
│   ├── course-manager/
│   ├── clickup-manager/
│   └── moodle-navigator/
│
├── gestionar-cursos/                 # Skill: extracción Moodle
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
│
├── use-clickup/                      # Skill: gestión ClickUp
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
│
└── universidad/                      # Persona agnóstica de plataforma
    ├── SKILL.md
    ├── references/
    └── scripts/
```

---

## Workflows

### Persona "Compañero de Universidad"

**Triggers de activación:**
- universidad, curso, clase, materia, bloque, periodo, semestre
- Moodle, ClickUp, tarea, entrega, parcial, examen, cuestionario, foro
- fecha límite, deadline, calificación, nota, evaluación
- sincronizar, actualizar, inicializar, bajar, organizar

**Comportamiento:**
1. Activar automáticamente por triggers
2. Leer estado cacheado (7 semanas)
3. Mostrar resumen al usuario
4. Ejecutar acciones usando `/gestionar-cursos` y `/use-clickup`
5. Actualizar índice local

---

## Tareas de Implementación

### 1. Archivado de Skills Antiguas

- [ ] **Paso 1:** Archivar `course-manager/`, `clickup-manager/`, `moodle-navigator/` a `archive/`
- [ ] **Paso 2:** Copiar scripts útiles a nuevas ubicaciones
  - `verify_workspace.py` → `gestionar-cursos/scripts/verify.py`
  - `clickup_client.py` → `use-clickup/scripts/client.py`

### 2. Implementar `/gestionar-cursos`

- [ ] **Paso 1:** SKILL.md con workflows `init`, `estado`
- [ ] **Paso 2:** Scripts de extracción (PGA, sesiones, unidades, materiales)
- [ ] **Paso 3:** Heurísticas (Teams, forcedownload, H5P)
- [ ] **Paso 4:** Referencias (guia-extraccion, heuristics, folder-structure)

### 3. Implementar `/use-clickup`

- [ ] **Paso 1:** SKILL.md con workflows esenciales
- [ ] **Paso 2:** `client.py` con API v3/v2, rate limiting, caching
- [ ] **Paso 3:** Scripts para tasks, lists, search
- [ ] **Paso 4:** Referencias (API completa)

### 4. Implementar Persona "Compañero de Universidad"

- [ ] **Paso 1:** SKILL.md con triggers y comportamiento
- [ ] **Paso 2:** `detectar_periodo.py` (derivar periodo de fechas)
- [ ] **Paso 3:** `index_manager.py` (cargar/guardar/validar cache)
- [ ] **Paso 4:** Referencias (time-awareness, index-format)

---

## Integración

### Flujo de Datos

```
Moodle (Source of Truth)
         ↓
/gestionar-cursos
  └── Materiales físicos (PDFs, DOCX, H5P proxies) + Metadata local
         ↓
/use-clickup
  └── Tasks con links a Moodle (NO path locales)
         ↓
Índice Local (.universidad_index.json)
  └── Mapeo: curso_code → list_id, task_ids
```

### Roles

| Skill | Propósito | Local | ClickUp |
|-------|-----------|-------|---------|
| `/gestionar-cursos` | Extraer materiales de Moodle | PDFs, DOCX, H5P proxies | Links a Moodle |
| `/use-clickup` | Gestionar actividades | Index (IDs) | Tasks, fechas, tags |
| Persona "Compañero" | Coordinar | Index + estado | Tracking completo |

---

## Referencias

- `docs/planes/2026-05-24-gestionar-cursos.md` — Plan detallado
- `docs/planes/2026-05-24-use-clickup.md` — Plan detallado
- `docs/planes/2026-05-24-universidad.md` — Plan persona