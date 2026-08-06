# PRD — use-mineru-cloud skill

## Goal

Domain skill: convert PDF / images / DOCX / PPTX / XLSX → high-quality Markdown
via MinerU cloud API (mineru.net). Works on any device with network — including
Termux phone (verified: reachable, SDK installable).

## Requirements

1. R1 — Two modes:
   - **precision** (token): full assets (markdown + images + content_list.json),
     200MB/200pg, model vlm|pipeline|html.
   - **flash** (no token): quick markdown only, 10MB/20pg.
2. R2 — Inputs: local file (presigned upload) or public URL. Batch multi-source.
3. R3 — Output: `<out>/<stem>.md` + `images/` + `<stem>_content_list.json`.
4. R4 — Auth: `MINERU_TOKEN` env ONLY. Skill MUST NOT contain/read/write secrets
   to disk. Public repo constraint.
5. R5 — Rate-limit aware: chunk batches ≤50 files/min; polling backoff
   2s→30s; timeout flags.
6. R6 — Agnostic (§9): behavior-only SKILL.md, harness/tool names banned,
   works via plain CLI script + any agent that reads SKILL.md.
7. R7 — Language default `en` (Andrés docs), `--language ch` for Chinese.

## Non-goals

- Local parsing → `use-mineru-local` (ClickUp Backlog, deferred).
- Web crawl is SDK bonus (crawl subcommand), not core.

## Success criteria

- `skill-forge audit` PASS.
- Live E2E on phone: convert a real PDF → markdown on device.
