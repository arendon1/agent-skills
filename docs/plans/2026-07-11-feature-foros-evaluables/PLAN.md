# PLAN: Evaluatable forums → main threads from classmates

## Tasks

| ID | Task | Status | Test |
|----|------|--------|------|
| F1 | `extraer_datos_foro(url)` reads the forum page: title, due date, instructions, activity, list of threads | [ ] | unit + manual against a real course |
| F2 | `extraer_discusiones_foro` without professor filter, cap 20, returns id+metadata | [ ] | unit |
| F3 | `extraer_primer_post_cached(discuss_id, url, cache_path)` with cache by `discuss_id` | [ ] | unit + manual: 2nd run does not re-open |
| F4 | `cli_foros.py`: new CLI that iterates the sidebar → detects evaluatable forums → extracts → saves in `Unidad-X/Foros/` | [ ] | manual: run against a real course |
| F5 | Hook in `cli_init.py` to run the forums flow during unit init | [ ] | manual: re-init a course |
| F6 | Hook in `cli_estado.py` to detect new threads in sync | [ ] | manual: add a thread in Moodle + sync |
| F7 | `scaffold_curso.py` creates `Unidad-X/Foros/` if it does not exist | [ ] | manual: init a new course |
| F8 | `SKILL.md` documents the new command and output | [ ] | visual |
| F9 | Propagate changes to `~/.agents/skills/gestionar-cursos/` (installed) | [ ] | diff |
| F10 | Commit + conventional commit message | [ ] | git log |

## Implementation Notes

### F1: extraer_datos_foro

Input: `url_foro: str`
Output: `dict` with:
```python
{
  "titulo": str,                    # e.g. "Foro 1: Seguridad en aplicaciones web (6%)"
  "vencimiento": str,               # ISO 8601 or ""
  "indicaciones": str,              # markdown of the instructions block
  "actividad": str,                 # markdown of the "Pregunta orientadora" block
  "es_evaluable": bool,             # True if "(X%)" in title and X>0
  "porcentaje": int,                # e.g. 6
  "url": str,
  "hilos": [                        # max 20
    {
      "discuss_id": str,            # e.g. "140651"
      "titulo": str,
      "autor": str,
      "fecha": str,                 # ISO 8601
      "ultimo_mensaje_autor": str,
      "ultimo_mensaje_fecha": str,
      "replicas": int,
      "url": str,                   # discuss.php?d=140651
    }
  ]
}
```

Selector strategy (based on a modern Moodle screenshot):
- Title: `h1` or `.page-header-headings h1`
- Due date: `div[data-region='activity-dates'] strong:contains('Vencimiento')` →
  parent's `.get_text` with a regex for the date
- Instructions: block under "Para participar siga las instrucciones..."
  → find the parent container of `<strong>` or the paragraph
  containing "Para participar siga las instrucciones"
- Activity: "Pregunta orientadora:" block → same pattern
- Threads: table `[data-region="discussion-list"]` or
  `table.forumheaderlist`
  - Each row: `a[href*="discuss.php"]` (title), following columns
    (author+date, last message+date, replies)

### F2: extraer_discusiones_foro refactor

- Remove the `nombre_profesor` parameter (no longer filtered by
  author)
- Add a cap of 20
- Return a list of `dict` with `discuss_id` (extracted from the URL
  with the regex `discuss\.php\?d=(\d+)`)

### F3: extract first post cached

```python
def extraer_primer_post_cached(discuss_id: str, url: str, cache: dict) -> str:
    if discuss_id in cache and "contenido" in cache[discuss_id]:
        return cache[discuss_id]["contenido"]
    contenido = _extraer_primer_post(url)
    if contenido is not None:
        cache[discuss_id] = {
            "contenido": contenido,
            "extraido_en": datetime.now().isoformat(),
        }
    return contenido
```

Cache: `_cache/foros_cache.json` per course (same dir as
`snapshot.json`).

### F4: cli_foros.py

Flow:
1. Load AGENTS.md → course URL
2. Extract sidebar (reuse `extraer_sidebar()`)
3. Filter only `tipo == "forum"`
4. For each forum:
   a. If section does not match `Unidad \d+` → skip (it is intro/announcements)
   b. Call `extraer_datos_foro(url)`
   c. If `es_evaluable == False` → skip
   d. Load cache `_cache/foros_cache.json`
   e. For each thread (cap 20): `extraer_primer_post_cached`
   f. Save cache
   g. Render markdown → `Unidad-X/Foros/<forum-slug>.md`

### F5-F6: hooks

In `cli_init.py` line 292 (`elif tipo == "forum":`), replace the
call to `extraer_discusiones_foro` with the new evaluatable forums
flow. Keep the intro flow intact in `_extraer_y_guardar_foros`.

In `cli_estado.py`, after extracting the sidebar, identify
evaluatable forums and compare cached vs current threads → report
new ones.

### F7: scaffold_curso.py

In `crear_estructura_curso`, after creating `Unidad-X/`, also create
`Unidad-X/Foros/` (empty, the files are filled in later).

### Output markdown template

```markdown
# Foro 1: Seguridad en aplicaciones web (6%)

- **URL:** https://aulavirtual.uniremington.edu.co/mod/forum/view.php?id=350767
- **Vencimiento:** 2026-07-19 23:59
- **Unidad:** Unidad 1
- **Hilos extraídos:** 5 (de 5 visibles)
- **Última actualización:** 2026-07-11

## Indicaciones

- Lea con atención las preguntas orientadoras.
- Evite copiar y pegar contenido generado por IA.
[...]

## Actividad a realizar

**Pregunta orientadora:**

1. ¿Cuál consideras...
2. ¿Qué rol juega...

## Hilos principales de compañeros

### 1. Amenazas de Seguridad (ID: 140651)

- **Iniciado por:** Juan Fernando Q... — 2026-07-07
- **Última respuesta:** Laura Vanesa Mo... — 2026-07-11
- **Réplicas:** 3
- **URL:** https://aulavirtual.uniremington.edu.co/mod/forum/discuss.php?d=140651

#### Primer post

[contenido completo, sin truncar]

---

### 2. Foro 1: Seguridad en aplicaciones web (ID: 140652)
[...]
```

## Test Strategy

- **Manual E2E:** run against a real Uniremington course that has at
  least 1 evaluatable forum with classmate threads. Verify:
  - File is generated in `Unidad-X/Foros/`
  - Metadata is correct (title, %, due date)
  - Threads listed with author, date, replies
  - First post content is complete
  - 2nd execution: cached threads are not re-opened
  - Forum without % is skipped
- **Syntax:** `python -c "import cli_foros"` + dry-run
- **Skill-forge audit:** validate that SKILL.md still follows the
  constitution

## Risks

- **R1:** Moodle HTML changes between courses/versions. Mitigation:
  multiple selectors with fallbacks (see the pattern in
  `extractor_modulos.py`).
- **R2:** Slow load with many threads. Mitigation: cap 20 + cache.
- **R3:** Course without "Unidad X" sections (custom names).
  Mitigation: if the section does not match the pattern, log a
  warning and skip (do not crash).
