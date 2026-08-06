---
name: use-mineru-cloud
description: >-
  Convert PDFs, images, DOCX, PPTX, and XLSX documents into clean Markdown via
  the MinerU cloud API (mineru.net) — headers/footers stripped, reading-order
  text, tables→HTML, formulas→LaTeX, OCR for scanned pages, images extracted
  alongside. Use when the user hands you a PDF (or document/image) to read,
  summarize, extract, or feed into a knowledge base; when they say "convert
  this PDF to markdown", "parse this document", "extract this paper", "make
  this readable"; when OCR of a scanned PDF is needed; when running on a
  lightweight device (phone/tablet) where local heavy parsing is impossible;
  or when batch-converting many documents at once. Two modes: flash (no token,
  fast, ≤10MB / ≤20 pages) and precision (Bearer token, full assets, ≤200MB /
  ≤200 pages, local-file upload). Never stores secrets — the token is read
  from the MINERU_TOKEN environment variable only.
invocation: auto
layer: domain
provides: [pdf-to-markdown]
language: en-US
metadata:
  version: "1.0.0"
  risk_tier: LOW
---

# use-mineru-cloud

## When (self-trigger)

- A PDF / image / DOCX / PPTX / XLSX file appears and needs reading, summarizing, extracting, or indexing.
- "Convert this PDF to markdown", "parse this document", "extract the text", "make this readable".
- Scanned PDF or image-heavy document needs OCR (109 languages).
- The device is lightweight (phone/tablet) — local heavy parsing is not an option.
- Batch conversion of many documents.
- Academic papers, reports, contracts, slides → markdown for RAG/knowledge base.

## What it does

Turns documents into high-quality Markdown using MinerU's cloud compute
(mineru.net). Output includes the markdown file, extracted images, and a
content-list JSON; optionally DOCX/HTML/LaTeX exports. No local model, no
heavy dependencies — only the official SDK (httpx-only) and network.

## Auth — secrets policy

- Precision modes read the token from the **`MINERU_TOKEN` environment variable**.
- The skill and its scripts NEVER write, print, or store the token. Do not put
  it in files, task descriptions, or configs (this repo is public).
- Flash mode needs no token at all.
- `mineru-cloud auth` verifies a token cheaply without consuming quota.

## Usage — `convert.py` (scripts/convert.py)

Run with any Python ≥ 3.10. Install the SDK once:
`python3 -m pip install mineru-open-sdk`

| Subcommand | Purpose | Token |
|---|---|---|
| `auth` | verify token (no quota cost) | yes |
| `convert <source> -o <out>` | single file or URL → `<out>/<stem>.md` + `images/` + `<stem>_content_list.json` | yes |
| `batch <s1> <s2> ... -o <out>` | many files/URLs → `<out>/<stem>/<stem>.md` each (chunked ≤50) | yes |
| `flash <source> -o <out>` | no-auth quick mode (≤10MB / ≤20 pages, markdown only) | no |
| `crawl <url> -o <out>` | web page → markdown (html model) | yes |

Common flags: `--language en` (default en; `ch` for Chinese), `--model
vlm|pipeline|html`, `--ocr`, `--no-formula`, `--no-table`, `--pages 1-20`,
`--format docx html latex`, `--timeout N`, `--stdout` (print markdown, save
nothing).

Examples:
```
export MINERU_TOKEN=...
python3 scripts/convert.py convert paper.pdf -o ./out --language en
python3 scripts/convert.py flash scanned.pdf -o ./out          # no token needed
python3 scripts/convert.py batch a.pdf b.pptx c.jpg -o ./out
python3 scripts/convert.py convert paper.pdf --stdout           # inline reading
```

## Workflow for the agent

1. **Classify** the input: scanned/image-heavy → `--ocr`; formulas → keep
   `--formula` (default on); Chinese → `--language ch`.
2. **Choose mode**: quick preview or tiny file → `flash`; full assets, big
   files, or local-file upload → `convert`.
3. **Foreign URLs** (github, aws, etc.) time out on the MinerU side — for such
   files download them locally first, then convert the local path (the script
   uploads via presigned URLs automatically).
4. **Output**: read `<out>/<stem>.md`; use `images/` for figure references;
   `content_list.json` for structured content when needed.
5. **Batch** large sets: the script chunks at 50 files/min (rate limit). Poll
   results via `--timeout` (default 300s single / 1800s batch).
6. **Failure**: `state=failed` prints `err_msg`. Typed errors (auth, too-large,
   page-limit, quota) map to clear messages — fix the input, don't retry blindly.

## Boundaries

- Precision: ≤200MB / ≤200 pages per file. Flash: ≤10MB / ≤20 pages.
- Rate limits: 50 files/min submit, 5,000/day (100 HTML), 1,000 req/min polling.
- 1,000 pages/day high-priority quota per account; beyond → slower queue.
- Local parsing (no network, own GPU) is a different skill (`use-mineru-local`,
  deferred) — do not fake it with this skill.
- The skill is a generic capability: no domain-specific rules (workspace ids,
  academic tags, course names) belong here.

## References

- `references/api.md` — full verified API contract (endpoints, options,
  limits, states, errors, SDK surface, gotchas). Read it when behavior is
  unclear or the API seems to have changed.
