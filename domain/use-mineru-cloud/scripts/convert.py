#!/usr/bin/env python3
"""
MinerU cloud converter — PDF / image / DOCX / PPTX / XLSX -> Markdown.

Backed by the official `mineru-open-sdk` (mineru.net cloud API). Works on any
device with network + Python >= 3.10 (incl. Termux on Android).

Subcommands:
  auth     Verify the MINERU_TOKEN works (cheap, consumes no quota).
  convert  Single source (local file OR public URL) -> <out>/<stem>.md + images/
  batch    Many sources -> <out>/<stem>/<stem>.md per file (rate-limit aware)
  flash    No-auth quick mode (max 10MB / 20 pages, markdown only)
  crawl    Web page URL -> markdown (uses the html model)

Auth: token is read from the MINERU_TOKEN environment variable for precision
modes. This script NEVER writes the token anywhere; pass it via env only.

Rate limits (mineru.net policy):
  - submit: 50 files/min (shared across all submit endpoints)
  - daily: 5,000 files (max 100 HTML)
  - get-results polling: 1,000 req/min
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

POLL_BACKOFF = 2.0       # seconds, doubles up to 30
POLL_MAX_BACKOFF = 30.0
SUBMIT_CHUNK = 50        # files per submit call (rate limit)


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def require_sdk() -> None:
    try:
        import mineru  # noqa: F401
    except ImportError:
        sys.exit(
            "mineru-open-sdk not installed.\n"
            "Install it with: python3 -m pip install mineru-open-sdk\n"
            "(httpx-only dependency; works on macOS, Linux, Termux/Android)"
        )


def get_token() -> str | None:
    tok = os.environ.get("MINERU_TOKEN")
    if not tok:
        log("MINERU_TOKEN not set — precision modes need it. Flash mode works without.")
    return tok


def poll_batch(client, batch_id: str, timeout: float) -> list:
    """Poll a batch until all results settle. Prints progress. Returns results."""
    from mineru import TimeoutError as MineruTimeout

    deadline = time.monotonic() + timeout
    interval = POLL_BACKOFF
    while True:
        results = client.get_batch(batch_id)
        states = [r.state for r in results]
        pending = [s for s in states if s not in ("done", "failed")]
        if not pending:
            return results
        # progress display
        for r in results:
            if r.progress and r.progress.total_pages:
                p = r.progress
                log(
                    f"  [{r.filename}] {r.state}: "
                    f"{p.extracted_pages}/{p.total_pages} pages"
                )
        if time.monotonic() > deadline:
            raise MineruTimeout(timeout, batch_id)
        time.sleep(min(interval, max(0.0, deadline - time.monotonic())))
        interval = min(interval * 2, POLL_MAX_BACKOFF)
    # unreachable


def save_result(result, out_dir: Path, stem: str) -> dict:
    """Persist markdown, images, content_list, extra formats. Returns saved paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: dict = {}
    if result.markdown:
        md_path = out_dir / f"{stem}.md"
        md_path.write_text(result.markdown, encoding="utf-8")
        saved["markdown"] = str(md_path)
    if result.images:
        img_dir = out_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        for img in result.images:
            (img_dir / img.name).write_bytes(bytes(img.data))
        saved["images"] = str(img_dir)
    if result.content_list:
        cl = out_dir / f"{stem}_content_list.json"
        cl.write_text(json.dumps(result.content_list, ensure_ascii=False, indent=1), encoding="utf-8")
        saved["content_list"] = str(cl)
    for fmt, attr in (("docx", "docx"), ("html", "html"), ("latex", "latex")):
        data = getattr(result, attr)
        if data is not None:
            target = out_dir / f"{stem}.{fmt}"
            if isinstance(data, bytes):
                target.write_bytes(data)
            else:
                target.write_text(str(data), encoding="utf-8")
            saved[fmt] = str(target)
    if result.error:
        saved["error"] = result.error
    return saved


def cmd_auth(args) -> int:
    from mineru import AuthError, MinerU, TaskNotFoundError

    tok = get_token()
    if not tok:
        return 1
    client = MinerU(tok)
    try:
        # getBatch with a bogus id authenticates without consuming quota:
        # AuthError -> bad token; TaskNotFound -> token valid.
        client.get_batch("00000000-0000-0000-0000-000000000000")
        log("auth: UNEXPECTED (no error) — treat as unknown")
        return 1
    except TaskNotFoundError:
        log("auth: PASS — MINERU_TOKEN is valid")
        return 0
    except AuthError as e:
        log(f"auth: FAIL — {e}")
        return 1
    finally:
        client.close()


def _build_options(args) -> dict:
    opts: dict = {}
    if args.model:
        opts["model"] = args.model
    if args.ocr:
        opts["ocr"] = True
    if args.formula is not None:
        opts["formula"] = args.formula
    if args.table is not None:
        opts["table"] = args.table
    if args.language:
        opts["language"] = args.language
    if args.pages:
        opts["pages"] = args.pages
    if args.format:
        opts["extraFormats"] = args.format
    if args.timeout:
        opts["timeout"] = args.timeout
    return opts


def cmd_convert(args) -> int:
    from mineru import MinerU

    tok = get_token()
    if not tok:
        return 1
    opts = _build_options(args)
    client = MinerU(tok)
    out = Path(args.out)
    try:
        if args.stdout:
            r = client.extract(args.source, **opts)
            if r.markdown:
                sys.stdout.write(r.markdown)
                return 0
            sys.exit(f"no markdown returned; state={r.state} error={r.error}")
        # manual submit + poll for progress visibility
        batch_id = client.submit(args.source, **opts)
        results = poll_batch(client, batch_id, opts.get("timeout", 300))
        r = results[0]
        if r.state == "failed":
            sys.exit(f"extraction failed: {r.error or r.errCode}")
        stem = Path(r.filename).stem if r.filename else (Path(args.source).stem if not _is_url(args.source) else "page")
        saved = save_result(r, out, stem)
        log(f"done: state={r.state}")
        for k, v in saved.items():
            log(f"  {k}: {v}")
        return 0
    finally:
        client.close()


def cmd_batch(args) -> int:
    from mineru import MinerU

    tok = get_token()
    if not tok:
        return 1
    opts = _build_options(args)
    client = MinerU(tok)
    out = Path(args.out)
    sources = args.sources
    try:
        for i in range(0, len(sources), SUBMIT_CHUNK):
            chunk = sources[i : i + SUBMIT_CHUNK]
            batch_id = client.submit_batch(chunk, **opts)
            log(f"submitted chunk {i // SUBMIT_CHUNK + 1}: {len(chunk)} files -> {batch_id}")
            results = poll_batch(client, batch_id, opts.get("timeout", 1800))
            for r in results:
                if r.state == "failed":
                    log(f"  FAILED {r.filename}: {r.error or r.errCode}")
                    continue
                stem = Path(r.filename or "out").stem
                saved = save_result(r, out / stem, stem)
                log(f"  ok {r.filename}: {saved.get('markdown')}")
        return 0
    finally:
        client.close()


def cmd_flash(args) -> int:
    from mineru import MinerU

    client = MinerU()
    opts: dict = {"timeout": args.timeout or 300}
    if args.language:
        opts["language"] = args.language
    if args.page_range:
        opts["pageRange"] = args.page_range
    if args.ocr:
        opts["ocr"] = True
    if args.formula is not None:
        opts["formula"] = args.formula
    if args.table is not None:
        opts["table"] = args.table
    try:
        r = client.flash_extract(args.source, **opts)
        if args.stdout:
            sys.stdout.write(r.markdown or "")
            return 0
        out = Path(args.out)
        stem = Path(args.source).stem if not _is_url(args.source) else "page"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{stem}.md").write_text(r.markdown or "", encoding="utf-8")
        log(f"done: {out / f'{stem}.md'}")
        return 0
    finally:
        client.close()


def cmd_crawl(args) -> int:
    from mineru import MinerU

    tok = get_token()
    if not tok:
        return 1
    client = MinerU(tok)
    try:
        r = client.crawl(args.url, timeout=args.timeout or 300)
        if args.stdout:
            sys.stdout.write(r.markdown or "")
            return 0
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "page.md").write_text(r.markdown or "", encoding="utf-8")
        log(f"done: {out / 'page.md'}")
        return 0
    finally:
        client.close()


def _is_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mineru-cloud",
        description="MinerU cloud: PDF/image/DOCX/PPTX/XLSX -> Markdown (mineru.net)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("auth", help="verify MINERU_TOKEN (no quota cost)")
    pa.set_defaults(fn=cmd_auth)

    pc = sub.add_parser("convert", help="single file or URL -> markdown + images")
    pc.add_argument("source", help="local file path or public http(s) URL")
    pc.add_argument("-o", "--out", default=".", help="output directory (default: cwd)")
    pc.add_argument("--stdout", action="store_true", help="print markdown, save nothing")
    _add_common(pc)
    pc.set_defaults(fn=cmd_convert)

    pb = sub.add_parser("batch", help="many files/URLs -> <out>/<stem>/ per file")
    pb.add_argument("sources", nargs="+", help="files and/or public URLs")
    pb.add_argument("-o", "--out", default=".", help="output directory (default: cwd)")
    _add_common(pb)
    pb.set_defaults(fn=cmd_batch)

    pf = sub.add_parser("flash", help="no-auth quick mode (10MB / 20 pages, md only)")
    pf.add_argument("source", help="local file path or public URL")
    pf.add_argument("-o", "--out", default=".", help="output directory")
    pf.add_argument("--stdout", action="store_true", help="print markdown, save nothing")
    pf.add_argument("--language", default="ch", help="OCR language (default ch)")
    pf.add_argument("--page-range", help="e.g. '1-10' or '5' (no commas)")
    pf.add_argument("--ocr", action="store_true", help="force OCR")
    pf.add_argument("--formula", dest="formula", action="store_true", default=None, help="formula recognition (default on)")
    pf.add_argument("--no-formula", dest="formula", action="store_false")
    pf.add_argument("--table", dest="table", action="store_true", default=None, help="table recognition (default on)")
    pf.add_argument("--no-table", dest="table", action="store_false")
    pf.add_argument("--timeout", type=int, help="max wait seconds (default 300)")
    pf.set_defaults(fn=cmd_flash)

    pw = sub.add_parser("crawl", help="web page URL -> markdown (html model)")
    pw.add_argument("url")
    pw.add_argument("-o", "--out", default=".", help="output directory")
    pw.add_argument("--stdout", action="store_true", help="print markdown, save nothing")
    pw.add_argument("--timeout", type=int, help="max wait seconds (default 300)")
    pw.set_defaults(fn=cmd_crawl)

    return p


def _add_common(sub) -> None:
    sub.add_argument("--model", choices=["vlm", "pipeline", "html"],
                     help="parsing model (default: auto — html for .html sources, else vlm)")
    sub.add_argument("--ocr", action="store_true", help="enable OCR (default off)")
    sub.add_argument("--formula", dest="formula", action="store_true", default=None, help="formula recognition (default on)")
    sub.add_argument("--no-formula", dest="formula", action="store_false")
    sub.add_argument("--table", dest="table", action="store_true", default=None, help="table recognition (default on)")
    sub.add_argument("--no-table", dest="table", action="store_false")
    sub.add_argument("--language", default="en", help="language (default en; ch for Chinese)")
    sub.add_argument("--pages", help="page range, e.g. '1-20'")
    sub.add_argument("--format", nargs="+", choices=["docx", "html", "latex"],
                     help="extra output formats alongside markdown/json")
    sub.add_argument("--timeout", type=int, help="max total wait seconds (default 300 single / 1800 batch)")


def main() -> int:
    require_sdk()
    args = build_parser().parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
