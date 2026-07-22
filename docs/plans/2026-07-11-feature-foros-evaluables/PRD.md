# PRD: Evaluatable forums → main threads from classmates

## Goal

Extract from every evaluatable forum (>0% in title) of a Moodle course:
title+%, due date, instructions, activity, and the main (root) threads
from classmates — only the first post, no replies — so the user can
scan, summarize, and decide where to participate.

## Why

Today `extractor_foro.py` filters only the professor's discussions
(intro use: Announcements, Consultations, Presentation). The user wants
the opposite pattern for activity forums: every main thread from any
author, with the forum description as "what to do", saved in the
corresponding unit's folder, not in `COMUNICACION/`.

## Scope

**Includes:**
- New extractor `extraer_datos_foro(url, section_name)` that reads the
  forum page and returns: `titulo`, `vencimiento`, `indicaciones`,
  `actividad`, `hilos` (list with id, title, author, date, last
  message, replies, URL).
- Modify `extraer_discusiones_foro`: remove the professor filter, add
  a cap of 20 threads, use a cache keyed by `discuss_id`.
- Function `extraer_primer_post_cached(discuss_id, url, cache)` that
  queries/updates the cache.
- New cache `_cache/foros_cache.json` with `discuss_id` as key.
- New CLI `cli_foros.py`: `gestionar-cursos foros <CARPETA_CURSO>`.
- Output: `Unidad-X/Foros/<forum-slug>.md` — one file per forum, with
  metadata + all threads inline (one per `##` section).
- Hook in `cli_init.py` and `cli_estado.py` to run the forums flow
  automatically during init/sync.
- "Is evaluatable" detection: regex `\((\d+)%\)` in the title. >0 →
  process; 0/no-match → skip.

**Does not include:**
- Replacement of the existing introductory forums flow (Announcements,
  Consultations, Presentation) in `COMUNICACION/`. That flow stays
  as-is.
- Scraping replies. Only the first post of each thread.
- LLM summary of threads (left as a future improvement).
- Automated E2E tests against Moodle (manual: run against a real
  course and verify).

## Acceptance

- [x] `uv run python cli_foros.py <CARPETA_CURSO>` processes a course
  and generates one `.md` per evaluatable forum in `Unidad-X/Foros/`.
- [x] Forums without a percentage in the title are skipped (no file
  generated).
- [x] Forums with `(0%)` or no match are skipped.
- [x] Each extracted thread includes: title, author, date, last
  message, replies, URL, full content of the first post.
- [x] Cap of 20 threads per forum (threads 21+ are skipped with a
  warning).
- [x] Re-execution uses the cache: already-extracted threads are not
  re-opened.
- [x] `cli_init.py` invokes the forums flow for `forum` activities in
  units (not in intro/announcements).
- [x] `cli_estado.py` detects new threads and extracts them; removed
  threads are flagged but do not delete the local file.
- [x] Introductory forums (Announcements, Consultations, Presentation)
  keep working as before.
- [x] `SKILL.md` documents the new command and behavior.

## Verification

- Unit smoke tests: `test_extractor_foro.py` (4 tests, all pass) —
  `es_evaluable`, `_parsear_fecha_es`, `extraer_hilos_listado`, cap
  of 20.
- Simulated E2E test: `test_cli_foros_integration.py` validates the
  markdown rendering with synthetic HTML based on the user's capture.
  All asserts pass.
- Compilation: `python3 -m py_compile` on the 5 modified files passes
  both in the source (`agent-skills-v2/domain/`) and in the
  installed copy (`~/.agents/skills/`).
- Pending: E2E test against a real Uniremington course. That
  requires an active Moodle session and is run manually by Andres
  after deploy.

## Out of Scope (future)

- Cache invalidation by timestamp (today the cache never expires,
  threads do not change in Moodle).
- LLM summarization of each thread.
- Auto-detection of "who I already replied to" (requires Moodle state
  about my posts).
- Attachment support in threads (images, files).
