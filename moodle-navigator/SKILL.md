---
name: moodle-navigator
description: >-
  Navigate Uniremington Moodle courses to verify activities, extract content, and check dates.
  Use when validating course information, finding specific forums or assignments,
  initializing new courses, or when user asks to check the "source of truth".
user-invocable: true
---

# Moodle Navigator

This skill defines the standard procedure for navigating the Uniremington Moodle portal (`aulavirtual.uniremington.edu.co`) to extract authoritative course information.

## 🛡️ Política de Autonomía y Portabilidad

- **Sin Dependencias Externas**: Este skill es 100% portable y autónomo. **Desestima** el uso de cualquier herramienta de sincronización externa como Monday.com, ClickUp o similares.
- **Autoridad Local**: El `sitemap.md` y `AGENTS.md` generados en la carpeta del curso son la única verdad fuera de Moodle.
- **Auto-Contenido**: Toda la lógica de extracción, organización y conversión reside en los scripts internos del skill.

## 🌍 Base Configuration

- **Base URL**: `https://aulavirtual.uniremington.edu.co`
- **My Courses**: `https://aulavirtual.uniremington.edu.co/my/courses.php`

## 🔐 Authentication Flow

Before any deep navigation, you MUST verify your permission state.

1. **Check Login**: Navigate to `https://aulavirtual.uniremington.edu.co/my/`.
2. **Verify State Indicators**:
    - **UNAUTHENTICATED**: If URL contains `login/index.php`, or you see "Usted no se ha identificado", or a "Acceder" button.
        - **ACTION**: Stop. Notify the user: "Please log in to Moodle manually in the browser."
        - **Tool**: Keep `open_browser` visible.
    - **AUTHENTICATED**: If you see your name (Andres Felipe Rendon Hernandez) or the "Área personal" heading.
        - **ACTION**: Proceed.

## 🔍 Course Discovery (Board-Driven)

If the user hasn't provided a specific URL, you must discover the course from the dashboard.

1. **Navigate**: Go to `https://aulavirtual.uniremington.edu.co/my/courses.php`.
2. **Scan Dashboard**: Look for the "Vista general de curso" list.
3. **Extract Metadata**: For each item, extract:
    - **Full Name**: e.g., "BASES DE DATOS 2 - 2601B04G1".
    - **Course Code**: The alphanumeric suffix (e.g., `2601B04G1`).
    - **URL**: The link behind the course name (permanent ID).
4. **User Confirmation**: Present the detected courses to the user and ask: "Which courses should I initialize/scaffold?"
5. **Proceed**: Use the selected URLs for the workflows below.

## 🚀 Course Management Workflows

### 🛠️ Self-Deployment

**CRITICAL**: If this skill is moved to a new workspace or slash commands are missing, run:
`python scripts/deploy_workflows.py`
This will proyect the `/curso-init` and `/curso-sync` workflows into the local `.agents/workflows` directory.

### 1. `/curso-init` (Deep Scaffolding)

**Use when**: Initializing a course for the first time or deep-mapping its metadata.

- **Action**:
    1. **Discover Available Courses**: Navigate to `my/courses.php`.
    2. **Scaffold Structure**: Create folders and seed `sitemap.md` via `scripts/scaffold_course.py`.
    3. **Deep Extraction**: Extract Teacher, PGA, Cronograma, and **full course section structure**.
    4. **Sitemap Generation**: The `sitemap.md` MUST contain permanent links to all found sections and relevant Moodle items.
    5. **Inference**: Derive Year/Semester/Block from the section text.
    6. **Verification & Cleanup**: Once initialized, you MUST review `AGENTS.md` and manually fill any remaining `[PENDIENTE]` placeholders using search tools or user interaction. Do not leave the file orphaned as a template.

### 2. `/curso-sync` (Sitemap & Content Indexing)

**Use when**: Keeping the course structure synchronized and indexing section links.

- **Action**:
    1. **Sidebar Extraction (Mandatory First Step)**:
        - **Navigate**: Go to the Course URL.
        - **Sidebar Sweep**: Open/Expand the Moodle sidebar and navigate item by item through ALL sections (General, Unidad 1, 2, 3, etc.).
        - **Index Permanent Links**: Extract the direct URL for every section and key activity found in the sidebar.
    2. **Sitemap Formation**:
        - Form/Update the `sitemap.md` structure strictly starting with the `## 🌐 Moodle Sections (Permanent Links)` section using the links newly extracted from the sidebar.
        - The `## 📂 Archivos Locales` section will be secondary.
    3. **Material Sync**:
        - Use the formed sitemap to touch each section and download materials (PDFs, DOCX).
        - Organize files into `Unidad-X/materiales/` as per rules in `moodle-folders.md`.
    4. **Tooling execution**:
        - Run `python scripts/sync_course.py [course_path]` to refresh the local file index and perform MD conversions.
    5. **Navigation Enforcement (The Lock)**:
        - **CRITICAL**: Once `sitemap.md` is populated with permanent links, the agent's reasoning is **LOCKED**. You MUST NOT perform any further blind navigation or re-scan the course. All future navigation requests for this course MUST resolve their target URL from `sitemap.md` first.

## 🧭 Navigation & UI Structure (Sitemap-Centric)

**Strict Rule**: You MUST prioritize `sitemap.md` for any navigation. Blind exploration is allowed ONLY if the sitemap is empty or outdated.

### Standard Sections

- **General / Introducción**: Syllabus, Announcements ("Avisos"), Forum ("Foro de Consultas"), Attendance.
- **Unidad 1, 2, 3...**: The core content modules.
  - **Resource Sections**: "Material de Estudio", "Recursos Educativos".
  - **Activity Sections**: "Actividades de Aprendizaje", "Evaluación".

### workflows

#### 1. Verify Activity Details

Use when user asks "Check if [Activity] exists" or "Verify [Activity] due date".

1. **Discover Course URL** (see above).
2. **Navigate** to the Course URL.
3. **Locate Activity**:
    - If the activity name implies a specific unit (e.g., "Parcial 1" is usually Unit 1 or 2), click that Unit tab first.
    - Otherwise, use the browser's "Find in page" or visual scan to locate the activity link.
4. **Extract Details**:
    - **Exact Name**: Copy precisely as shown.
    - **Due Date**: Open the activity and look for "Fecha de entrega" or "Cierre".
    - **Status**: Check if it accepts submissions.

#### 2. Check Announcements

1. Navigate to Course URL.
2. Go to **"General"** or **"Introducción"** tab.
3. Find forum named **"Avisos"**, **"Novedades"**, or **"Noticias"**.
4. Extract the subjects and dates of the last 3 posts.

## 🛡️ Heurística de Captura de Links (Teams)

Al extraer el **Cronograma de Sesiones Sincrónicas**, utiliza esta heurística estricta para asegurar la validez y **seguridad** de los enlaces:

1. **Captura Directa Únicamente**: SOLO captura y registra enlaces que apunten directamente a `teams.microsoft.com/l/meetup-join/`.
2. **Prohibición de Redirecciones**: Por seguridad, **NO navegues ni captures** enlaces que utilicen acortadores (e.g., `bit.ly`) o recursos de redirección interna de Moodle (`mod/url/view.php`). Si un enlace no es directo de Teams, **ignóralo**.
3. **Búsqueda Alternativa**: Si el cronograma contiene solo enlaces de redirección, busca en la sección "Introducción" o "General" un recurso tipo URL que sea un enlace directo verificable.
4. **Marcado de Incertidumbre**: Si no se encuentra un enlace directo a Teams que cumpla con el dominio `microsoft.com`, deja el campo como `[PENDIENTE: Link no seguro o inexistente]` e informa al usuario.
5. **Validación Final**: Asegúrate de que el enlace sea de **reunión** y no un enlace a una carpeta de SharePoint o grabación de Teams.

## 📥 Heurística de Descarga Forzosa (PDFs y Archivos)

Para evitar que el navegador abra los archivos (especialmente PDFs) en lugar de descargarlos, sigue esta regla al capturar cualquier enlace de material:

1. **Detección de Archivos**: Si el enlace apunta a `pluginfile.php` o parece ser un recurso de archivo de Moodle.
2. **Parámetro de Descarga**: Asegúrate de que el enlace incluya el parámetro `forcedownload=1`.
    - Si el enlace ya tiene parámetros (contiene `?`), añade `&forcedownload=1`.
    - Si no tiene parámetros, añade `?forcedownload=1`.
3. **Aplicación**: Aplica esto tanto en `sitemap.md` como en `AGENTS.md` y cualquier otra referencia a materiales descargables.

## 🧠 Best Practices

- **Source of Truth**: Moodle is the absolute authority. If local files (README, AGENTS.md) differ, update them to match Moodle.
- **Date Parsing**: Be careful with relative dates ("in 2 days"). Always look for absolute dates (e.g., "Sunday, 15 February 2026, 23:59").
- **Files**: If asked to download, verify the file link is accessible and not restricted.
