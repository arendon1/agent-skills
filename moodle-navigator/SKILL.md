---
name: moodle-navigator
description: >-
  Navigate Uniremington Moodle courses to verify activities, extract content, and check dates.
  Use when validating course information against Monday.com, finding specific forums or assignments,
  initializing new courses, or when user asks to check the "source of truth".
user-invocable: true
---

# Moodle Navigator

This skill defines the standard procedure for navigating the Uniremington Moodle portal (`aulavirtual.uniremington.edu.co`) to extract authoritative course information.

## 🌍 Base Configuration

- **Base URL**: `https://aulavirtual.uniremington.edu.co`
- **My Courses**: `https://aulavirtual.uniremington.edu.co/my/courses.php`

## 🔐 Authentication Flow

Before attempting any deep navigation or extraction, you MUST verify authentication status.

1. **Check Login**: Navigate to `https://aulavirtual.uniremington.edu.co/my/`.
2. **Verify State**:
    - **IF** redirected to `login/index.php` or see "Usted no se ha identificado":
        - **ACTION**: Stop. Notify the user they must log in.
        - **Message**: "Please log in to Moodle to continue."
        - **Tool**: use `open_browser` to show the login page if not already visible.
        - **Wait**: Ask user to confirm when they have logged in.
    - **IF** see "Área personal" or course dashboard:
        - **ACTION**: Proceed with the task.

## 🔍 Course Discovery (Dynamic)

**CRITICAL**: Do NOT use hardcoded Course IDs. You must dynamically discover the correct Moodle URL for the requested course.

1. **Search Workspace**: Look for a folder matching the course name in `c:\Users\andres.rendon\Documents\Universidad\2026-1-1`.
2. **Read Configuration**: Open the `AGENTS.md` file inside that course folder.
3. **Extract URL**: Find the line starting with `- **URL Moodle**:` or containing the full course URL (e.g., `https://aulavirtual.uniremington.edu.co/course/view.php?id=XXXXX`).
4. **Use Authoritative Source**: This extracted URL is the **only** valid destination for the course.

## 🚀 Initialize New Courses (Deep Mapping)

Use this workflow when the user wants to "map" or "initialize" courses from Moodle.

1. **Navigation**: Go to `https://aulavirtual.uniremington.edu.co/my/courses.php`.
2. **List Available**: Extract the list of all courses (Name + Link) visible on the page.
3. **Prompt User**: Present the list to the user and **ask them to select** which courses to initialize. (Do NOT assume all courses should be processed).
4. **For EACH selected course**:

    a. **Scaffold Structure**:
       - Run the scaffolding script to create folders and `AGENTS.md` template.
       - Command: `uv run .agent/skills/moodle-navigator/scripts/scaffold_course.py "[Course Name]" "[Moodle URL]"`

    b. **Deep Extraction**:
       - Navigate to the Course URL.
       - **Section: General / Introducción**:
         - **Teacher**: Extract Name/Email from "Conoce tu profesor" or similar label.
         - **Academic Plan**: Find the table "Plan de Gestión Académica" (DO-FR-66). Extract activities, weights, and dates.
         - **Schedule**: Find "Cronograma de Sesiones Sincrónicas". Extract dates, times, and **Teams/Recording links**.

    c. **Populate AGENTS.md**:
       - Edit the newly created `[Course Name]/AGENTS.md`.
       - Fill in the `[PENDIENTE]` fields with the extracted data.
       - Ensure the "Sistema de Evaluación" table matches the DO-FR-66 data.
       - Ensure the "Cronograma" table matches the extracted schedule info.

## 🧭 Navigation & UI Structure

Uniremington Moodle courses follow a standard tabbed or grid layout. Understand this structure to find content efficiently.

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

## 🧠 Best Practices

- **Source of Truth**: Moodle is the absolute authority. If local files (README, Monday.com) differ, update them to match Moodle.
- **Date Parsing**: Be careful with relative dates ("in 2 days"). Always look for absolute dates (e.g., "Sunday, 15 February 2026, 23:59").
- **Files**: If asked to download, verify the file link is accessible and not restricted.
