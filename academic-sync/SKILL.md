---
name: academic-sync
description: >-
  Orquesta Moodle Navigator y ClickUp Manager para sincronizar cursos académicos.
  Usa cuando necesites inicializar cursos, documentar metadatos (README/AGENTS) o sincronizar actividades académicas.
metadata:
  version: "1.0.0"
  language: es-CO
---

# 🎓 Academic Sync (Uniremington)

Este skill es un orquestador especializado para la gestión académica en la Uniremington. No contiene scripts de API propios, sino que utiliza `clickup-manager` y `moodle-navigator` para realizar sus tareas.

## 🛠️ Requisitos

Para que este skill funcione, el agente debe tener acceso a:

1. **ClickUp Manager**: Configurado con `CLICKUP_PAT`.
2. **Moodle Navigator**: Capaz de acceder a la plataforma de la Uniremington.

## 🔄 Flujos Integrados (Workflows)

### 1. Inicialización de Curso (`workflows/curso-init.md`)

**Uso**: "Inicializar curso [Nombre] para el Bloque [N]"

- Extrae metadatos precisos de Moodle (Introducción).
- Crea la estructura de carpetas en ClickUp (AÑO-SEMESTRE-BLOQUE).
- Genera `README.md` (para humanos) y `AGENTS.md` (para LLMs) en la carpeta local del curso.

### 2. Sincronización de Actividades (`workflows/curso-sync.md`)

**Uso**: "Sincronizar actividades del curso [Nombre]"

- Lee el `AGENTS.md` local para obtener el contexto.
- Extrae la tabla `DO-FR-66` de Moodle.
- Sincroniza en ClickUp usando heurística inteligente para evitar duplicaciones.

## 📚 Estructura de Datos

El proyecto sigue el estándar:

- **Folder**: `[AÑO]-[SEMESTRE]-[BLOQUE]`
- **List**: `[Nombre del Curso]`
