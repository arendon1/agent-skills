# Context: gestionar-cursos

## Glossary

| Term | Definition |
|------|------------|
| **Moodle Instance** | The aulavirtual.uniremington.edu.co platform. No API access for students. |
| **Course Scaffolding** | The automated creation of local folder structure (AGENTS.md, PGA.md, Unidad-X/, etc.) from Moodle data. |
| **Course Index Drawer** | Left sidebar in Moodle (`#theme_boost-drawers-courseindex`) listing all sections and activities. Rendered server-side. |
| **SSR** | Server-Side Rendering. Moodle course structure is fully SSR — no JS/AJAX required for extraction. |
| **Module Type** | Moodle activity type: `page`, `resource`, `forum`, `quiz`, `assign`, `url`, `label`, `hvp`. Each has different page structure. |
| **Sitemap** | Tree of all sections and activity links extracted from the course index drawer. |
| **H5P Proxy** | Local HTML file that embeds H5P interactive content via iframe pointing to Moodle. Requires internet. Not truly offline. |

## Discovered Facts

- Course structure (drawer with sections + activities) is fully server-side rendered.
- No JavaScript execution needed to extract the sitemap.
- `requests + session cookies + BeautifulSoup` is sufficient for data extraction.
- Only the Microsoft OAuth login step requires a browser (Chrome).
- After login, cookies are exported from Chrome to `requests.Session` for all scraping.
- Session cookies are persisted to disk (`.moodle_session.json`) with 7-day TTL for subsequent runs.

## Module Page Structures (Inspected)

| Type | Page Content | Extraction Target |
|------|-------------|-------------------|
| `page` | Title + rich HTML content | Full text/markdown of the page |
| `resource` | Title + download link to PDF | Download URL (`pluginfile.php`) |
| `forum` | Title + discussion list (author, date, replies) | **All first-level (root) discussions by the professor** — original post content only, no replies |
| `quiz` | Title + deadline + instructions + attempts + grade rules | Deadline, instructions, attempt limits, grade thresholds |
| `hvp` | Title + iframe with interactive content | Embed URL for local HTML proxy |
| `folder` | Title + list of files | File list with download URLs |

## Content Conversion

### HTML → Markdown
- Library: `markdownify` (declared in `requirements.txt`).
- Source: `#region-main` or `.course-content` of each `page` module.
- Output: `.md` file per page activity.

### Image Handling
- Images embedded in `page` content use `pluginfile.php` URLs.
- **Offline-first**: download all images to `Unidad-X/materiales/imagenes/`.
- Rewrite markdown image paths to local relative paths.

### Documentos Introductorios (Módulo, Microcurrículo, etc.)
- **Not stored as files.** Their text content is extracted and merged into `README.md`, `AGENTS.md`, and `context.md`.
- Soporta: PDF, DOCX/DOC, XLSX/XLS, PPTX/PPT.
- Unit-level resources are still downloaded to `Unidad-X/materiales/`.

## Extraction Strategy

### Phase 1: Sitemap (from course index drawer)
- Parse `#theme_boost-drawers-courseindex` once.
- Build tree: sections → activities → URLs.
- No page visits needed.

### Phase 2: Per-Module Detail (link-by-link)
- For each activity URL, visit and extract based on module type.
- **Intro `page`**: extract → `README.md` + `context.md` + `AGENTS.md`
- **Unit `page`**: extract `#region-main` → convert to markdown with `markdownify` → `Unidad-X/contenido/`.
- **Forum**: extract **first discussion only** → `COMUNICACION/forum_name.md`.
- **Quiz**: extract deadline, instructions, attempt count, time limit, passing grade → `Unidad-X/actividades/`.
- **Resource**: extract `pluginfile.php` download URL → `MATERIA/` or `Unidad-X/materiales/`.
- **Folder**: extract file list → `Unidad-X/materiales/`.
- **H5P**: create proxy HTML with `embed.php?id=XXX` → `Unidad-X/materiales/`.

## Extraction vs. Sitemap Decision Matrix

| Type | Needs Detail Page? | Why |
|------|-------------------|-----|
| `page` | **Yes** | Content varies per page. Must visit to extract text. |
| `resource` | **Yes** | Need actual `pluginfile.php` URL for download. |
| `forum` | **Yes** | First post has professor's instructions. |
| `quiz` | **Yes** | Deadline, instructions, grade rules only on detail page. |
| `hvp` | **Yes** | Need embed URL for proxy. |
| `folder` | **Yes** | Need file list inside folder. |
| `label` | **No** | Inline text only, no separate page. **Ignored.** |

## Re-initialization Behavior

When `cli_init.py` runs on an already-initialized course:

1. **Detection:** Checks if `AGENTS.md` exists in target folder.
2. **Redirect:** If exists → runs `_sync_curso()` instead of scaffold.
3. **Merge strategy (selective):**
   - Sections marked `<!-- auto -->` in `AGENTS.md` are refreshed from Moodle.
   - Sections marked `<!-- manual -->` are preserved.
   - New activities in Moodle are appended to sitemap/PGA.
   - Modified dates in Moodle update corresponding entries.
   - Manual fields (PERIOD, BLOCK) edited by user are never overwritten.

## Checkpointing

- File: `.progress.json` en la carpeta del curso.
- Guarda: course_url, completed activities, pending activities, timestamp.
- Created at start of sync. Updated after each processed activity.
- Cleared on successful completion.
- Enables resumption if session expires mid-extraction.

## Error Handling Policy

- **Resilient — never fails completely.**
- Each activity: retry 3× with exponential backoff (1s, 2s, 4s).
- After retries exhausted: skip activity, log warning, continue with next.
- Report skipped activities at end of run.
- **Session expired:** detect redirect to login → save checkpoint → pause → prompt user for re-login → resume from checkpoint.
- Checkpoint prevents loss of progress across re-authentication.
