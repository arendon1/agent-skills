# MinerU cloud API — verified contract (2026-08-06)

Source: official SDK source (`mineru-open-sdk` PyPI/npm 0.2.5, Apache-2.0),
mineru.net apiManage docs, live endpoint probes. Skill engine: `convert.py`.

## Auth

- Token from `https://mineru.net/apiManage`. Env: `MINERU_TOKEN`.
- Header: `Authorization: Bearer <token>`.
- Flash mode needs NO auth.
- `convert.py auth` verifies a token cheaply (getBatch with bogus id —
  AuthError = bad token, TaskNotFound = valid; no quota consumed).

## Endpoints (precision, base https://mineru.net/api/v4)

| Purpose | Method + path | Body → response |
|---|---|---|
| Submit URLs | `POST /extract/task/batch` | `{files:[{url, is_ocr?, page_ranges?, data_id?}], model_version, enable_formula?, enable_table?, language?, extra_formats?}` → `{data:{batch_id}}` |
| Local files | `POST /file-urls/batch` | `{files:[{name, ...same fields}]}` → `{data:{batch_id, file_urls:[presigned PUT urls]}}` then `PUT` bytes per url |
| Poll batch | `GET /extract-results/batch/{batch_id}` | `{data:{extract_result:[{task_id, file_name, state, err_code, err_msg, full_zip_url, extract_progress:{extracted_pages, total_pages, start_time}}]}}` |
| Poll single | `GET /extract/task/{task_id}` | same result shape |
| Result | download `full_zip_url` | zip: `full.md`, `images/*`, `*_content_list.json`, `layout.json`, `model.json`, `origin.pdf` (+ docx/html/latex if `extra_formats`) |

## Endpoints (flash, base https://mineru.net/api/v1/agent — no auth)

| Purpose | Method + path | Notes |
|---|---|---|
| URL | `POST /parse/url` | `{url, language, page_range?, is_ocr?, enable_formula?, enable_table?}` → `{data:{task_id}}` |
| File | `POST /parse/file` | multipart (signed upload flow) |
| Poll | `GET /parse/{task_id}` | markdown only |

## Models & options

- `model`: `vlm` (default) | `pipeline` | `html`; auto-inferred — `.html/.htm` → `html`, else `vlm`.
- Defaults: `ocr` off, `formula` on, `table` on, `language "ch"`, pages=all.
- `pages` format: `"1-20"` (single-source only); flash uses `page_range` `"1-10"` or `"5"`.
- `extra_formats`: subset of `["docx","html","latex"]` alongside default md+json.

## Limits & rate policy (official)

| Surface | Limit |
|---|---|
| Submit (single + batch + URL share) | 50 files/min |
| Daily | 5,000 files (max 100 HTML) |
| Get results (single + batch share) | 1,000 req/min |
| Precision file | 200MB / 200 pages |
| Flash file | 10MB / 20 pages |
| Priority quota | 1,000 pages/day high priority; beyond → lower priority |
| Foreign URLs (github, aws…) | time out — prefer CDN/own-hosted URLs |

Polling: 2s→30s backoff is well under 1,000 req/min. Chunk submits ≤50 files.

## States & errors

`state`: `pending | running | converting | done | failed`.

SDK typed errors: `AuthError, ParamError, FileTooLargeError, PageLimitError,
TaskNotFoundError, ExtractFailedError, TimeoutError, QuotaExceededError,
NoAuthClientError` (+ Flash variants). Agent loops key off `state` + `progress`.

## Official SDK surface (Python, mirrors JS)

- `MinerU(token=None, base_url=..., flash_base_url=...)` — token from `MINERU_TOKEN`.
- `extract(source, options)` / `extract_batch(sources)` / `crawl(url)` /
  `flash_extract(source, options)` — blocking, poll internally.
- `submit(source)` / `submit_batch(sources)` → `batch_id`; `get_batch(batch_id)` /
  `get_task(task_id)` — manual polling. NOTE: `submit` returns a BATCH id even
  for single files; `get_task` only for ids obtained elsewhere.
- Result attrs (snake_case): `task_id, state, filename, err_code, error,
  zip_url, progress{extracted_pages,total_pages}, markdown, content_list,
  images[{name,data,path}], docx, html, latex`.
- Helpers: `save_markdown(path, with_images=True)`, `save_all(dir)`.
- `set_source("app-name")` for attribution. `client.close()`.

## Gotchas

- Python attr names are snake_case (`content_list`), JS camelCase — do not
  mix when reading results.
- URL sources: the zip/result `filename` gives the real name; source stem is
  only a fallback (`page`).
- Precision default language is `ch`; for en/es docs pass `--language en`.
- Submitting a URL means THEIR servers fetch it — network-restricted to
  China-friendly hosts. For foreign files, download locally then upload
  (file-urls presigned flow), which `convert.py` does automatically for local paths.
