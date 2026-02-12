---
name: monday-course-manager
description: >-
  Administra un tablero de Monday.com para gestión académica.
  Use cuando el usuario quiera organizar cursos, tareas o ver su calendario académico en Monday.
license: Apache-2.0
metadata:
  version: "1.0.0"
  trit: 0
  author: agent-builder
compatibility: Requires Monday.com API key and board access
---

# Monday Course Manager Skill

Este skill capacita a un subagente (o al usuario) para configurar y administrar eficazmente un tablero en Monday.com dedicado al seguimiento de cursos universitarios y sus actividades académicas.

## 1. Estructura del Tablero (Board Architecture)

Para maximizar la organización, el tablero debe estructurarse de la siguiente manera:

### Grupos (Groups)

Cada **Grupo** representa una **Asignatura / Curso** del semestre actual.

* **Ejemplo**: "Matemáticas Discretas", "Programación II", "Ética Profesional".
* **Grupo Adicional**: "Actividades Extracurriculares" o "Administrativo" (opcional).

### Elementos (Items)

Cada **Elemento** dentro de un grupo es una **Actividad Específica** o entregable.

* No usar elementos para conceptos abstractos; deben ser tareas accionables (ej: "Leer Cap. 4", "Entregar Taller 1", "Parcial 2").

### Columnas (Columns)

Configura las siguientes columnas para cada tablero:

1. **Estado (Status)**:
    * `Sin Iniciar` (Gris - Default)
    * `En Progreso` (Azul/Amarillo)
    * `Bloqueado / Ayuda` (Rojo)
    * `Revisión` (Naranja)
    * `Completado` (Verde)
2. **Fecha (Date)**: "Fecha de Entrega" (Due Date). Fundamental para la vista de Calendario.
3. **Prioridad (Status/Label)**:
    * `Alta` (Rojo)
    * `Media` (Amarillo)
    * `Baja` (Azul)
4. **Tipo de Actividad (Dropdown/Status)**:
    * `Examen`, `Taller`, `Lectura`, `Proyecto`, `Quiz`.
5. **Enlace (Link)**: URL al material de estudio, enunciado o entrega (LMS/Moodle/Drive).
6. **Calificación (Numbers)**: Para registrar la nota obtenida (opcional).
7. **Archivos (Files)**: Para adjuntar el entregable final o evidencia.

## 2. Flujos de Trabajo (Workflows)

### Al Inicio del Semestre (Setup)

1. **Crear el Tablero**: Usar la plantilla "Student Organizer" o crear desde cero con la estructura anterior.
2. **Poblar Actividades**: Revisar el *Syllabus* de cada curso e ingresar TODAS las fechas importantes (parciales, entregas grandes) como elementos.
3. **Asignar Prioridades**: Marcar exámenes y proyectos finales como `Prioridad Alta` desde el día 1.

### Rutina Semanal (Weekly Review)

El agente debe ejecutar esta rutina cada lunes o domingo:

1. **Revisión de Fechas**: Filtrar por "Esta Semana" y asegurar que todo tenga estado `En Progreso`.
2. **Actualización de Estados**: Mover tareas terminadas a `Completado`.
3. **Desbloqueo**: Identificar tareas en `Bloqueado` y generar un plan de acción (buscar tutoría, preguntar al profesor).

### Gestión de Entregas (Submission)

1. Cuando una tarea esté lista, subir el archivo a la columna **Archivos** (manualmente o vía enlace).
2. Cambiar estado a `Completado` usando `update_item.py` o interfaz web.
3. Si es un enlace, actualizar la columna **Enlace**.

## 3. Flujo Interactivo de Configuración (Interactive Setup)

Para garantizar que el agente opere sobre el tablero correcto y mantenga la sincronización:

### 1. Descubrimiento (Discovery)

El agente debe ejecutar el script `scripts/list_boards.py` para obtener una lista JSON de todos los tableros disponibles en la cuenta de Monday asociada a la API Key.

* **Comando**: `python scripts/list_boards.py`
* **Acción**: Presentar los nombres e IDs al usuario y preguntar cuál desea administrar.

### 2. Persistencia (Configuration)

Una vez el usuario seleccione un tablero, el agente debe guardar esta preferencia usando `scripts/save_config.py`.

* **Comando**: `python scripts/save_config.py <BOARD_ID> "<BOARD_NAME>"`
* **Resultado**: Se crea el archivo `.monday_config.json`, que será usado automáticamente por los otros scripts.

### 3. Sincronización Continua (Sync Loop)

El agente **siempre** debe corroborar su caché local antes de tomar decisiones críticas o asumir estados.

* **Al iniciar sesión**: Ejecutar `python scripts/sync_cache.py`.
* **Antes de completar una tarea**: Ejecutar `sync_cache.py` para asegurar que no haya sido modificada externamente.
* **Al completar una tarea**: Ejecutar `python scripts/update_item.py <ITEM_ID> <COLUMN_ID> <VALUE>` para reflejar el cambio en Monday inmediatamente.

## 4. Automatizaciones Recomendadas (Automations)

Si el agente tiene permisos de configuración en Monday, debe sugerir o implementar:

* "Cuando la fecha llegue y el estado no sea Completado, notificarme."
* "Cuando el estado cambie a Completado, mover a grupo 'Logros' (opcional, si se usa un grupo de archivo)."
* "3 días antes de la fecha límite, cambiar estado a 'Atención' si sigue 'Sin Iniciar'."

## 5. Gestión de Caché Local y API (Scripts)

Este skill incluye scripts en Python para interactuar con la API de Monday.

### Requisitos Previos

1. Instalar dependencias: `pip install -r scripts/requirements.txt`
2. Configurar API Key en `.env`: `MONDAY_API_KEY=...`

### Scripts Disponibles

* `list_boards.py`: Lista todos los tableros accesibles.
* `save_config.py`: Guarda la configuración del tablero seleccionado.
* `sync_cache.py`: Descarga el estado actual del tablero a `.monday_cache.json`. Usa la configuración guardada por defecto.
* `update_item.py`: Actualiza el valor de una columna (Estado, Fecha, Texto) de un elemento específico.
  * Uso: `python update_item.py <ITEM_ID> <COLUMN_ID> <VALUE>`
  * Ejemplo: `python update_item.py 12345 status "Completado"`

## 6. Instrucciones para el Subagente

Al interactuar con este tablero, el subagente debe:

1. **Configuración Inicial**: Si no existe `.monday_config.json`, iniciar el flujo de descubrimiento y selección.
2. **Leer caché**: Leer `.monday_cache.json` para entender el estado actual.
3. **Verificar**: Si la información parece desactualizada o crítica, ejecutar `sync_cache.py` antes de actuar.
4. **Actualizar**: Al cambiar un estado, usar `update_item.py` y luego confirmar con `sync_cache.py`.
5. **Proactividad**: Alertar sobre fechas próximas basándose en la columna "Fecha".
