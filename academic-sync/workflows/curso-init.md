---
description: Inicializa un curso académico extrayendo metadatos de Moodle y preparando ClickUp y documentación local.
---

# 🏗️ Inicialización de Curso (Scaffolding & Docs)

Este flujo prepara el entorno de trabajo para un curso específico.

## 1. Identificación y Extracción (Moodle)

- Navegar a la sección **"> Introducción"** del curso en Moodle.
- **Extraer con precisión**:
  - Nombre oficial del curso.
  - Nombre del Docente y correo de contacto (usualmente en **"Conoce tu profesor"**).
  - Cronograma base o avisos importantes.
  - URL base del curso y **enlaces permanentes de cada sección** (e.g. Introducción, Unidad 1, etc.).
  - **Documentación Clave** (Acceder y extraer texto/docs):
    - **"Visión general del curso"** (Contenido descriptivo).
    - **"Conoce tu profesor"** (Perfil y contacto).
    - **"Material complementario de materia"** (o similar; recursos base).

## 2. Documentación Local (Cámara de Información)

En el directorio de trabajo del usuario (donde se gestiona el semestre), crear:

### `README.md` (Vista Humana)

- Título con el nombre del curso.
- Sección de **Contacto Docente**.
- Resumen de la metodología mencionada en Moodle.
- Enlace directo al curso.

### `AGENTS.md` (Contexto para LLMs)

- Tabla de metadatos técnicos:
  - `COURSE_ID`: Extraído de la URL.
  - `CLICKUP_LIST_ID`: (Se llenará en el paso 4).
  - `MOODLE_URL`: URL completa.
  - `PERIOD`: YEAR-HALF-BLOCK.
- **Mapeo de Secciones**:
  - Lista de nombres de secciones y sus URLs permanentes (`section.php?id=...`) para navegación directa.
- Instrucciones específicas para el agente sobre cómo manejar este curso.

## 3. Estructura de Carpetas Local

- **Paso Preliminar**: Verificar si ya existe una estructura de carpetas en el directorio del curso.
- Si no existe o está incompleta, crear las siguientes subcarpetas:
  - `assets/`: Para imágenes, diagramas y capturas.
  - `docs/`: Para documentos PDF, lecturas y material extraído.
  - `logs/`: Para registros de ejecución de agentes o notas temporales.
- Organizar los archivos `README.md` y `AGENTS.md` en la raíz de esta estructura.

## 4. Estructura de ClickUp

- Inferir **AÑO** y **SEMESTRE** (Ene-Jun = 1, Jul-Dic = 2).
- Solicitar al usuario el **BLOQUE** (1, 2, o 3).
- Usar `clickup-manager` para:
  1. Localizar/Crear carpeta `[YEAR]-[HALF]-[BLOCK]`.
  2. Crear lista `[Course Name]`.
  3. Obtener el `LIST_ID` y guardarlo en el `.env` local y en el `AGENTS.md`.

## 🧠 Instrucciones para el Agente

- Sé extremadamente preciso con los nombres. Si el curso se llama "PROGRAMACIÓN I", ese debe ser el nombre en ClickUp.
- Si el `README.md` o `AGENTS.md` ya existen, **Actualízalos** con nueva información en lugar de sobrescribirlos ciegamente.
