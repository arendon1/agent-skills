#!/usr/bin/env python3
"""
Busca artículos académicos usando la API de EXA (exa-py >= 2.x).

Usa los endpoints modernos del SDK (`Exa.search`, `Exa.find_similar`,
`Exa.get_contents`, `Exa.answer`). Los antiguos `search_and_contents` y
`find_similar_and_contents` están deprecados en exa-py 2.x.

Salida:
  - JSON estructurado con metadatos de cada artículo encontrado
    (compatible con `merge_results.py` y con el skill `generar-paper`).
  - Opcionalmente BibTeX para integración directa con gestores de referencias.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Any

EXA_API_KEY = os.getenv("EXA_API_KEY")
if not EXA_API_KEY:
    print(
        "Error: EXA_API_KEY no está configurada. "
        "Establecela con: export EXA_API_KEY=tu-clave",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    from exa_py import Exa  # type: ignore
except ImportError:
    print(
        "Error: exa-py no está instalado. Instalalo con: pip install exa-py",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Action dispatch — mirror of the pi `exa_search` tool
# ---------------------------------------------------------------------------

ACTION_SEARCH = "search"
ACTION_SIMILAR = "similar"
ACTION_CONTENTS = "contents"
ACTION_ANSWER = "answer"

VALID_ACTIONS = (ACTION_SEARCH, ACTION_SIMILAR, ACTION_CONTENTS, ACTION_ANSWER)

# exa-py categories (subset; full list lives in the SDK)
VALID_CATEGORIES = (
    "company",
    "people",
    "research paper",
    "news",
    "pdf",
    "github",
    "tweet",
    "personal site",
    "linkedin profile",
    "financial report",
)
VALID_SEARCH_TYPES = ("auto", "instant", "neural", "fast", "deep-lite", "deep", "deep-reasoning")
VALID_ANSWER_MODELS = ("exa", "exa-pro")


# ---------------------------------------------------------------------------
# Query rewriting for `search` (back-compat: keep `author:` / `intitle:` syntax)
# ---------------------------------------------------------------------------

def build_search_query(args: argparse.Namespace) -> str:
    parts = [args.query]
    if args.author:
        parts.append(f"author:{args.author}")
    if args.title_contains:
        parts.append(f"intitle:{args.title_contains}")
    return " ".join(parts).strip()


# ---------------------------------------------------------------------------
# Shared filter / contents builders
# ---------------------------------------------------------------------------

def build_filters(args: argparse.Namespace) -> dict[str, Any] | None:
    f: dict[str, Any] = {}
    if args.include_domains:
        f["include_domains"] = [d.strip() for d in args.include_domains.split(",") if d.strip()]
    if args.exclude_domains:
        f["exclude_domains"] = [d.strip() for d in args.exclude_domains.split(",") if d.strip()]
    if args.include_text:
        f["include_text"] = [t.strip() for t in args.include_text.split(",") if t.strip()]
    if args.exclude_text:
        f["exclude_text"] = [t.strip() for t in args.exclude_text.split(",") if t.strip()]
    if args.start_published_date:
        f["start_published_date"] = args.start_published_date
    if args.end_published_date:
        f["end_published_date"] = args.end_published_date
    if args.start_crawl_date:
        f["start_crawl_date"] = args.start_crawl_date
    if args.end_crawl_date:
        f["end_crawl_date"] = args.end_crawl_date
    return f or None


def build_contents(args: argparse.Namespace) -> dict[str, Any] | None:
    """Map CLI flags onto the modern `contents` shape (text / highlights / summary)."""
    if args.full_text:
        max_chars = args.max_characters if args.max_characters > 0 else 5000
        return {"text": {"max_characters": max_chars}}
    if args.highlights:
        return {"highlights": True}
    if args.summary:
        return {"summary": True}
    return None


# ---------------------------------------------------------------------------
# Action handlers — each returns a dict compatible with merge_results.py
# ---------------------------------------------------------------------------

def run_search(args: argparse.Namespace, exa: Exa) -> dict[str, Any]:
    if not args.query:
        sys.exit("Error: --action=search requiere `query`.")
    query_str = build_search_query(args)

    params: dict[str, Any] = {"query": query_str}
    contents = build_contents(args)
    if contents is not None:
        params["contents"] = contents

    if args.limit:
        params["num_results"] = args.limit
    if args.category:
        params["category"] = args.category
    if args.type:
        params["type"] = args.type
    if args.additional_queries:
        params["additional_queries"] = [
            q.strip() for q in args.additional_queries.split("|") if q.strip()
        ]
    if args.user_location:
        params["user_location"] = args.user_location
    if args.system_prompt:
        params["system_prompt"] = args.system_prompt
    filters = build_filters(args)
    if filters:
        params.update(filters)

    print(f"Buscando en EXA (search): {query_str}", file=sys.stderr)
    print(f"Parámetros: {json.dumps({k: v for k, v in params.items() if k != 'system_prompt'})}", file=sys.stderr)

    response = exa.search(**params)
    formatted = [_format_result(r, source=ACTION_SEARCH) for r in response.results]
    return {
        "query": query_str,
        "action": ACTION_SEARCH,
        "timestamp": datetime.now().isoformat(),
        "sources_used": ["exa"],
        "total_results": len(formatted),
        "results": formatted,
    }


def run_similar(args: argparse.Namespace, exa: Exa) -> dict[str, Any]:
    if not args.url:
        sys.exit("Error: --action=similar requiere --url.")
    params: dict[str, Any] = {"url": args.url}
    contents = build_contents(args)
    if contents is not None:
        params["contents"] = contents
    if args.limit:
        params["num_results"] = args.limit
    if args.category:
        params["category"] = args.category

    # apply only the relevant filters
    if args.include_domains:
        params["include_domains"] = [d.strip() for d in args.include_domains.split(",") if d.strip()]
    if args.exclude_domains:
        params["exclude_domains"] = [d.strip() for d in args.exclude_domains.split(",") if d.strip()]
    if args.include_text:
        params["include_text"] = [t.strip() for t in args.include_text.split(",") if t.strip()]
    if args.exclude_text:
        params["exclude_text"] = [t.strip() for t in args.exclude_text.split(",") if t.strip()]
    if args.start_published_date:
        params["start_published_date"] = args.start_published_date
    if args.end_published_date:
        params["end_published_date"] = args.end_published_date
    if args.start_crawl_date:
        params["start_crawl_date"] = args.start_crawl_date
    if args.end_crawl_date:
        params["end_crawl_date"] = args.end_crawl_date

    print(f"Buscando en EXA (similar): {args.url}", file=sys.stderr)
    response = exa.find_similar(**params)
    formatted = [_format_result(r, source=ACTION_SIMILAR) for r in response.results]
    return {
        "query": args.url,
        "action": ACTION_SIMILAR,
        "timestamp": datetime.now().isoformat(),
        "sources_used": ["exa"],
        "total_results": len(formatted),
        "results": formatted,
    }


def run_contents(args: argparse.Namespace, exa: Exa) -> dict[str, Any]:
    urls: list[str] = []
    if args.urls:
        urls = [u.strip() for u in args.urls.split(",") if u.strip()]
    elif args.url:
        urls = [args.url]
    else:
        sys.exit("Error: --action=contents requiere --urls (CSV) o --url.")

    params: dict[str, Any] = {
        "urls": urls,
        "text": {"max_characters": args.max_characters if args.max_characters > 0 else 5000},
    }
    print(f"Buscando en EXA (contents): {urls}", file=sys.stderr)
    response = exa.get_contents(**params)
    formatted = [_format_result(r, source=ACTION_CONTENTS) for r in response.results]
    return {
        "query": ",".join(urls),
        "action": ACTION_CONTENTS,
        "timestamp": datetime.now().isoformat(),
        "sources_used": ["exa"],
        "total_results": len(formatted),
        "results": formatted,
    }


def run_answer(args: argparse.Namespace, exa: Exa) -> dict[str, Any]:
    if not args.question:
        sys.exit("Error: --action=answer requiere --question.")
    params: dict[str, Any] = {"query": args.question, "text": bool(args.full_text)}
    if args.model:
        params["model"] = args.model
    if args.system_prompt:
        params["system_prompt"] = args.system_prompt
    if args.user_location:
        params["user_location"] = args.user_location

    print(f"Preguntando a EXA (answer): {args.question}", file=sys.stderr)
    response = exa.answer(**params)
    citations = []
    for c in response.citations:
        citations.append(
            {
                "title": getattr(c, "title", None),
                "authors": _coerce_authors(getattr(c, "author", None)),
                "year": _extract_year(getattr(c, "published_date", None)),
                "doi": None,
                "url": getattr(c, "url", None),
                "abstract": (getattr(c, "text", None) or "")[:500] if args.full_text else None,
                "source": ACTION_ANSWER,
            }
        )
    return {
        "query": args.question,
        "action": ACTION_ANSWER,
        "timestamp": datetime.now().isoformat(),
        "sources_used": ["exa"],
        "total_results": len(citations),
        "answer": response.answer,
        "results": citations,
    }


# ---------------------------------------------------------------------------
# Result shaping — keep schema stable for merge_results.py
# ---------------------------------------------------------------------------

def _format_result(r: Any, source: str) -> dict[str, Any]:
    text = getattr(r, "text", None)
    summary = getattr(r, "summary", None)
    highlights = getattr(r, "highlights", None)
    entry: dict[str, Any] = {
        "title": getattr(r, "title", None) or "Sin título",
        "authors": _coerce_authors(getattr(r, "author", None)),
        "year": _extract_year(getattr(r, "published_date", None)),
        "doi": None,
        "url": getattr(r, "url", None) or "",
        "abstract": _pick_abstract(text, summary, highlights),
        "source": source,
    }
    url = entry["url"]
    if url and "doi.org/" in url:
        entry["doi"] = url.split("doi.org/", 1)[1]
    return entry


def _pick_abstract(text: str | None, summary: str | None, highlights: list[str] | None) -> str | None:
    """Pick the best abstract-shaped field. Used by merge_results.py."""
    if summary:
        return summary[:500]
    if text:
        return text[:500]
    if highlights:
        joined = " ".join(highlights)
        return joined[:500]
    return None


def _coerce_authors(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(a) for a in raw if a]
    return [str(raw)]


def _extract_year(published: Any) -> int | None:
    if not published:
        return None
    try:
        match = re.match(r"(\d{4})", str(published))
        return int(match.group(1)) if match else None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# BibTeX export
# ---------------------------------------------------------------------------

def to_bibtex(payload: dict[str, Any]) -> str:
    entries: list[str] = []
    used_keys: set[str] = set()

    for i, r in enumerate(payload["results"]):
        cite_key = _make_cite_key(r, i)
        if cite_key in used_keys:
            suffix = ord("a")
            while f"{cite_key}{chr(suffix)}" in used_keys:
                suffix += 1
            cite_key = f"{cite_key}{chr(suffix)}"
        used_keys.add(cite_key)

        lines = [f"@article{{{cite_key},"]
        lines.append(f"  title = {{{r.get('title', '')}}},")
        authors = r.get("authors") or []
        if authors:
            lines.append(f"  author = {{{' and '.join(authors)}}},")
        if r.get("year"):
            lines.append(f"  year = {{{r['year']}}},")
        if r.get("doi"):
            lines.append(f"  doi = {{{r['doi']}}},")
        if r.get("url"):
            lines.append(f"  url = {{{r['url']}}},")
        lines.append("}")
        entries.append("\n".join(lines))

    return "\n\n".join(entries)


def _make_cite_key(result: dict[str, Any], index: int) -> str:
    authors = result.get("authors") or []
    year = result.get("year", "????")
    if authors:
        last_name = authors[0].split()[-1].lower().replace(",", "")
        return f"{last_name}{year}"
    return f"ref{index + 1}{year}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Busca artículos académicos usando la API moderna de EXA.",
        epilog="Requiere EXA_API_KEY en variable de entorno.",
    )
    p.add_argument(
        "--action",
        choices=VALID_ACTIONS,
        default=ACTION_SEARCH,
        help="Operación EXA: search (default), similar, contents, answer.",
    )

    # ---- search / similar shared ----
    p.add_argument(
        "query_pos",
        nargs="?",
        default=None,
        help=argparse.SUPPRESS,  # hidden positional that aliases --query for back-compat
    )
    p.add_argument("--query", help="Tema o frase de búsqueda (acción=search).")
    p.add_argument("--url", help="URL fuente (similar) o único URL (contents).")
    p.add_argument(
        "--urls",
        help="Lista de URLs separadas por coma para contents (alternativa a --url).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Número máximo de resultados (default: 10).",
    )
    p.add_argument(
        "--category",
        choices=VALID_CATEGORIES,
        help="Filtro vertical EXA: research paper, news, github, etc.",
    )
    p.add_argument(
        "--type",
        choices=VALID_SEARCH_TYPES,
        help="Motor de búsqueda EXA: auto (default), neural, deep, ...",
    )

    # ---- search-only ----
    p.add_argument("--author", help="Filtrar por autor (`author:<name>` se agrega al query).")
    p.add_argument(
        "--title-contains",
        help="Palabras obligatorias en el título (`intitle:` se agrega al query).",
    )
    p.add_argument(
        "--include-domains",
        help="Whitelist de dominios separados por coma.",
    )
    p.add_argument(
        "--exclude-domains",
        help="Blacklist de dominios separados por coma.",
    )
    p.add_argument(
        "--include-text",
        help="Cadenas separadas por coma que DEBEN aparecer en la página.",
    )
    p.add_argument(
        "--exclude-text",
        help="Cadenas separadas por coma que NO deben aparecer.",
    )
    p.add_argument(
        "--start-published-date",
        help="Fecha ISO (YYYY-MM-DD). Lower bound en publishedDate.",
    )
    p.add_argument(
        "--end-published-date",
        help="Fecha ISO (YYYY-MM-DD). Upper bound en publishedDate.",
    )
    p.add_argument(
        "--start-crawl-date",
        help="Fecha ISO. Lower bound en crawlDate.",
    )
    p.add_argument(
        "--end-crawl-date",
        help="Fecha ISO. Upper bound en crawlDate.",
    )
    p.add_argument(
        "--additional-queries",
        help="Queries alternativos separados por `|` para búsqueda deep (max 5).",
    )
    p.add_argument("--user-location", help="Código ISO de país de 2 letras, ej. US.")
    p.add_argument(
        "--system-prompt",
        help="Prompt que guía el LLM de síntesis / answer.",
    )

    # ---- contents / shape ----
    p.add_argument(
        "--full-text",
        action="store_true",
        help="Devuelve el texto completo de cada página (text.contents).",
    )
    p.add_argument(
        "--highlights",
        action="store_true",
        help="Devuelve highlights en lugar de texto completo.",
    )
    p.add_argument(
        "--summary",
        action="store_true",
        help="Devuelve un resumen LLM en lugar de texto completo.",
    )
    p.add_argument(
        "--max-characters",
        type=int,
        default=5000,
        help="Cap de caracteres por página cuando --full-text (default: 5000).",
    )

    # ---- answer-only ----
    p.add_argument("--question", help="Pregunta (acción=answer).")
    p.add_argument(
        "--model",
        choices=VALID_ANSWER_MODELS,
        help="Modelo EXA para `answer`: exa o exa-pro.",
    )

    # ---- output ----
    p.add_argument("--output", help="Archivo de salida (si se omite, imprime a stdout).")
    p.add_argument(
        "--format",
        choices=["json", "bibtex"],
        default="json",
        help="Formato de salida (default: json).",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    # Resolve the optional positional into --query so all documented examples
    # (`search_exa.py "free-text query"`) keep working.
    if args.query is None and getattr(args, "query_pos", None):
        args.query = args.query_pos
    exa = Exa(EXA_API_KEY)  # type: ignore[arg-type]

    try:
        if args.action == ACTION_SEARCH:
            payload = run_search(args, exa)
        elif args.action == ACTION_SIMILAR:
            payload = run_similar(args, exa)
        elif args.action == ACTION_CONTENTS:
            payload = run_contents(args, exa)
        elif args.action == ACTION_ANSWER:
            payload = run_answer(args, exa)
        else:  # argparse `choices` already gates this
            sys.exit(f"Acción no soportada: {args.action}")
    except Exception as e:
        sys.stderr.write(f"Error en EXA {args.action}: {e}\n")
        sys.exit(1)

    if args.format == "bibtex":
        output_str = to_bibtex(payload)
    else:
        output_str = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)
        print(f"Resultados guardados en {args.output}", file=sys.stderr)
    else:
        print(output_str)


if __name__ == "__main__":
    main()
