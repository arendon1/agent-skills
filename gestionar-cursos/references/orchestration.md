# Orchestration Guide: Course Manager

This guide defines how to delegate tasks to specialized university management agents.

## 🤖 Specialized Roles

| Role | Purpose | Strategy |
| :--- | :--- | :--- |
| **Syllabus Analyst** | Extract dates and topics from PDFs/Moodle. | WHERE: `Introduccion/`, WHAT: Microcurrículo. |
| **Deadline Tracker** | Sync PGA dates to ClickUp. | WHERE: `AGENTS.md`, WHAT: PGA Table. |
| **Material Organizer** | Download and classify Moodle files. | WHERE: Moodle URLs, WHAT: `Unidad-X/materiales`. |

## 🚀 Parallel Initialization

When initializing multiple courses, use the following pattern:

1. **Discovery Agent**: Run a loop to list all courses from `my/courses.php`.
2. **Parallel Dispatch**: For each course, spawn a `Course Scaffolder` agent.
3. **Synchronization**: Each scaffolder runs `scaffold_course.py` and then reports back to the orchestrator.

## 📋 Delegation Template (WHERE, WHAT, WHY)

**WHERE**: `[Course Path]`
**WHAT**: `[Specific Document or Action]`
**WHY**: `[Educational Goal, e.g., Prepare for Exam 1]`

**TASK**:

1. Run `python scripts/verify_workspace.py .` to ensure context integrity.
2. Proceed with [Action].
3. Update `AGENTS.md` with findings.
