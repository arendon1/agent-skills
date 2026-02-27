---
name: course-manager
description: >-
  Personal assistant for university management (Uniremington).
  Orchestrates Moodle Navigator and ClickUp Manager to sync courses, track deadlines, and manage study materials.
  Use when initializing courses, automating academic sync, or orchestrating study agents in parallel.
metadata:
  version: "2.0.0"
  language: es-CO
  trit: 0
  risk_tier: CAUTION
---

# 🎓 Course Manager (Uniremington)

Este es un orquestador integral para la gestión de tu vida universitaria. A diferencia de su predecesor, es totalmente autocontenido y soporta flujos multi-agente en paralelo para una configuración ultra-rápida.

## 🛠️ Estructura y Dependencias

Este skill consume sus dependencias internamente desde `.agent/skills/`:

1. **Moodle Navigator**: Fuente de verdad para materiales y scaffolding.
2. **ClickUp Manager**: Gestión de tareas y cronogramas.

## 📚 Referencias Especializadas

| Guía | Propósito |
| :--- | :--- |
| `references/orchestration.md` | Cómo lanzar agentes en paralelo para múltiples cursos. |
| `references/context-patterns.md` | Estándares de "Context Signal" para AGENTS.md. |
| `scripts/verify_workspace.py` | Suite de pruebas para verificar la integridad del curso. |

## 🔄 Flujos Core

### 1. Inicialización en Paralelo (`workflows/curso-init.md`)

**Uso**: "Inicializa mis cursos del bloque 2 en paralelo"

- Lanza sub-agentes para cada curso.
- Ejecuta el scaffolding estándar de Moodle Navigator.
- Valida la estructura final con la suite de pruebas.

### 2. Sincronización Personal (`workflows/curso-sync.md`)

**Uso**: "Sincroniza mis fechas de entrega de [Asignatura]"

- Mapea el PGA de Moodle directamente a listas de ClickUp.
- Evita duplicados mediante heurística de nombre y fecha.

## 📋 Reglas de Oro

- **No duplicación**: Siempre verifica si el curso ya existe localmente antes de re-descargar.
- **Limpieza de Contexto**: Usa `verify_workspace.py` tras procesar textos largos para asegurar que el workspace esté impecable.
