# RESEARCH — MinerU (cloud + local) for use-mineru skills

> Synthesized 2026-08-05 from: cloned repo opendatalab/MinerU@master (v3.4.4),
> official SDK packages `mineru-open-sdk` (PyPI + npm, v0.2.5, extracted + read
> full source), pi docs `termux.md`, live probes of mineru.net API endpoints.

## TL;DR

- Cloud API (mineru.net) is **the right primary path**: official, free tier,
  token auth, works from any device with HTTP. Pi runs on Termux (official docs)
  — Node 18+ and Python 3.10+ both available there → cloud skill deployable to phone.
- Local MinerU on Termux: **NOT feasible** (torch + opencv + multi-GB models,
  no Android ARM64 support). Cloud-for-phone / local-for-powerful-devices split
  is correct.
- Two official SDKs mirror each other exactly: **Python** `mineru-open-sdk`
  (dep: httpx only, py>=3.10) and **JS** `mineru-open-sdk` (dep: fflate only,
  Node>=18). Either works on macOS + Termux. Python chosen (repo uses uv/python).
- Flash API needs **no auth** (10MB/20pg, markdown only). Precision API needs
  token (200MB/600pg, full assets). Skill should expose both modes.

## A. Product facts (repo README, docs/en)

- MinerU = OpenDataLab doc parser: PDF, image, DOCX, PPTX, XLSX → Markdown/JSON.
- v3.4.4 pip latest. License: custom MinerU OSL (Apache-2.0-based) since v3.1;
  was AGPLv3 before. SDKs: Apache-2.0.
- Removes headers/footers/footnotes/page numbers; reading-order text; tables→HTML;
  formulas→LaTeX; OCR 109 langs; scanned-PDF auto-detect; images + descriptions.
- Backends: `pipeline` (CPU-ok), `vlm-engine`, `hybrid-engine` (default, effort
  `medium`|`high`), `*-http-client` (OpenAI-compatible remote). Hybrid default
  `effort=medium` (~35-220% faster, no image-analysis; `high` for max accuracy).
- Local CLI: `mineru -p <in> -o <out> [-b backend] [--effort] [-m auto|txt|ocr]
  [-f/-t formula/table] [--image-analysis] [-s/-e page range] [-l lang]`.
  Auto CUDA/MPS. Models from huggingface (default) or modelscope
  (`MINERU_MODEL_SOURCE=modelscope`).
- Server mode: `mineru-api` FastAPI — `POST /tasks` (async), `POST /file_parse`
  (sync), `GET /tasks/{id}[/result]`, `GET /health`; tasks retained 24h.
  `mineru-router` = multi-GPU load-balanced entry (compatible with mineru-api).
- Heavy deps: torch, opencv-python, models = multiple GB. Docker available.

## B. Cloud API (mineru.net) — verified contract

- Token: https://mineru.net/apiManage (also `https://mineru.net/apiManage/docs`).
  Env var `MINERU_TOKEN`. Auth: `Authorization: Bearer <token>`.
- Base URL: `https://mineru.net/api/v4`. Verified live: `POST /api/v4/file-urls/batch`
  → 401 "login required" without token (endpoint exists).

### Precision flow (auth) — from SDK source
1. `POST /extract/task/batch` — URL sources
   body `{ files: [{url, is_ocr?, page_ranges?, data_id?}], model_version,
   enable_formula?, enable_table?, language?, extra_formats? }`
   → `{data: {batch_id}}`
2. Local files: `POST /file-urls/batch` body `{files:[{name, ...same fields}]}`
   → `{data: {batch_id, file_urls: [presigned PUT urls]}}`, then `PUT` bytes per url.
3. Poll `GET /extract-results/batch/{batch_id}` → `{data:{extract_result:[...]}}`
   or `GET /extract/task/{task_id}` (single, when task id known).
4. Result fields: `task_id, state(pending|running|done|failed), file_name,
   err_code, err_msg, full_zip_url, extract_progress{extracted_pages,total_pages,
   start_time}`. On done → download zip → `*.md` + images + `*_content_list.json`
   (+ docx/html/latex if `extra_formats`).
- Limits: 200MB / 600 pages per file.
- Defaults: `ocr` off, `formula` on, `table` on, `language "ch"`, pages=all.
  Model inference: `.html/.htm` → `"MinerU-HTML"`, else `"vlm"` (options: vlm|pipeline|html).

### Flash flow (NO auth) — verified from SDK source
- Base: `https://mineru.net/api/v1/agent`.
- `POST /parse/url` body `{url, language, page_range?, is_ocr?, enable_formula?,
  enable_table?}` → task_id; `POST /parse/file` (multipart); `GET /parse/{task_id}`.
- Markdown only (no images/assets). Limits: 10MB / 20 pages.

### Errors (typed in SDK)
`AuthError, ParamError, FileTooLargeError, PageLimitError, TaskNotFoundError,
ExtractFailedError, TimeoutError, QuotaExceededError, NoAuthClientError` (+Flash
variants). Agent loops key off `state` + `progress`.

## C. Official SDKs (both Apache-2.0, same surface)

| Package | Where | Deps | Env |
|---|---|---|---|
| `mineru-open-sdk` 0.2.5 | PyPI (py>=3.10) | httpx only | MINERU_TOKEN |
| `mineru-open-sdk` 0.2.5 | npm (Node>=18) | fflate only | MINERU_TOKEN |
| `mineru-open-api` 0.5.9 | npm native CLI | platform binary (darwin-arm64 ✅, NO android) | MINERU_TOKEN |
| `mineru-mcp` 1.1.4 | npm MCP server | — | MINERU_TOKEN |

- Methods: `extract / extract_batch / crawl / crawl_batch / flash_extract` (blocking);
  `submit / submit_batch / get_task / get_batch` (async primitives);
  `save_markdown / save_all / ...` helpers. `set_source("app")` for attribution.
- Python client: `MinerU(token=None, base_url=..., flash_base_url=...)`,
  `client.close()`, context manager. Same defaults/polling as JS (2s→30s backoff).
- Source repos: opendatalab/MinerU-Ecosystem (SDKs), opendatalab/MinerU (core).

### Limits & rate policy (official, 2026-08-06)

| Surface | Limit |
|---|---|
| Submit (single + batch + URL share) | **50 files/min** |
| Submit daily | **5,000 files/day** (max 100 HTML files) |
| Get results (single + batch share) | **1,000 req/min** |
| Precision file | 200MB / 200 pages (docs) — SDK README says 600 pages, docs say 200; trust docs |
| Flash file | 10MB / 20 pages |
| Priority | 1,000 pages/day highest-priority per account; beyond → lower priority |
| Callback | POST with signature (seed param, user-defined) |
| Network | github/aws/foreign URLs time out (Chinese service) — use CDN/own-hosted URLs |

Polling implication for skill: 2s→30s backoff is fine vs 1,000 req/min; batch caps at
50 files/min per submit call — chunk large batches.

## D. Termux / Pi feasibility — CONFIRMED (live phone verification 2026-08-05)

- Pi officially supports Termux: `docs/termux.md` — `pkg install nodejs termux-api git`,
  `npm i -g --ignore-scripts @earendil-works/pi-coding-agent`, run `pi`.
- Termux has nodejs AND python (`pkg install python`). Both SDKs run on phone.
- Constraints: optional native deps skipped (clipboard module); shared storage via
  `termux-setup-storage` → `/storage/emulated/0`; no image clipboard.
- **Local MinerU on phone: NOT feasible** (torch/opencv/models, Android ARM64
  unsupported). Cloud = correct phone path. Local = macOS/Linux/GPU machines.

### Live phone probe (ssh phone → 192.168.1.20:8022, user u0_a332)

| Check | Result | Impact |
|---|---|---|
| arch | `aarch64` | torch/opencv wheels unavailable |
| node | v26.4.0 | JS SDK (Node>=18) OK |
| python | 3.14.6 | py SDK (>=3.10) OK; **local `mineru` pip requires `<3.14` → would fail anyway** |
| git / npm / uv | 2.55.0 / 12.0.1 / 0.11.29 | toolchain complete |
| pi | installed at `/data/data/com.termux/files/usr/bin/pi` | runnable |
| RAM | 10Gi total, ~3.1Gi free | heavy local inference impossible |
| mineru.net | `POST /api/v4/file-urls/batch` → **401 in 1.2s** | cloud API reachable, needs token |
| pypi | 200 | `pip install mineru-open-sdk` works on phone |
| storage | `/storage/emulated/0/{Download,Documents,...}` readable | termux-setup-storage done; PDFs accessible |
| skills | 239 in `~/.pi/agent/skills` → symlink to `~/.agents/skills` (lock-managed, rsync from Mac) | deploy = copy skill dir to phone `.agents/skills` |
| MINERU_TOKEN | absent on phone | token must be provisioned (env or config) |

**Skill deployment to phone** = manual rsync/scp from Mac into `~/.agents/skills/`
(AppleDouble `._*` markers confirm macOS copy). No repo deploy script exists.

## E. Skill split recommendation

- `use-mineru-cloud` (domain, `provides: [pdf-to-markdown]`): wraps cloud API via
  Python SDK (httpx only). Modes: flash (no auth, quick) + precision (token, full).
  Works everywhere incl. Termux. Token from env `MINERU_TOKEN`.
- `use-mineru-local` (domain, `provides: [pdf-to-markdown]`): wraps local `mineru`
  CLI for powerful devices. Gate: skip when Termux/mobile detected. Heavy install
  + model download handled lazily.
- Both generic capabilities — no domain-specific constraints (§12). No code
  imports between skills (§12). Adapter-agnostic: pure CLI/scripts.
- Optional later: `mineru-open-api` native CLI or `mineru-mcp` for MCP harnesses.

### Token verification (2026-08-06) — Bearer token WORKS end-to-end

- User's AK/SK pair (`oldr6ggn...` / `yqkwqnj...`) was for a different service —
  all auth forms vs v4 API → 401 `A0202 user authenticate failed` or `login required`. Discarded.
- Valid token: `sk-...` (from mineru.net apiManage). Proven E2E with raw curl:
  1. `POST /api/v4/file-urls/batch` → 200, `batch_id` + presigned Aliyun OSS PUT url.
  2. `POST /api/v4/extract/task/batch` `{files:[{url}], enable_formula, enable_table, language}` → `batch_id`.
  3. `GET /api/v4/extract-results/batch/{id}` → `state=done` in ~6s, `full_zip_url`.
  4. Zip contains `full.md` (51KB), `images/` (20), `*_content_list.json`, `layout.json`, `model.json`, `origin.pdf`.
- Official Python SDK `mineru-open-sdk` 0.2.5 (httpx only): URL extract done in 2.8s;
  local-file upload (presigned flow) done in 12.2s. Both return markdown + 20 images.
- Flash API (no auth) verified: `POST /api/v1/agent/parse/url` → task_id (works tokenless).
- Token storage: `MINERU_TOKEN` env var (SDK convention). Phone lacks it — provision step needed.

## Sources
- https://github.com/opendatalab/MinerU (README, docs/en, pyproject.toml)
- https://mineru.net/apiManage (token) + /docs/usage-guide (docs SPA)
- PyPI `mineru-open-sdk` 0.2.5 (wheel read in full)
- npm `mineru-open-sdk` 0.2.5 (dist/index.js read in full)
- pi docs `/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent/docs/termux.md`
- Live probes: mineru.net/api/v4 endpoints (401/405/404 as expected)
