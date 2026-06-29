#!/usr/bin/env python3
"""
Busca artículos académicos usando la API de EXA.

Usa el SDK `exa-py` para búsqueda semántica con filtros por categoría,
rango de fechas, dominios y texto incluido. Requiere la variable de entorno
EXA_API_KEY configurada con una clave válida de EXA.

Salida:
  - JSON estructurado con metadatos de cada artículo encontrado.
  - Opcionalmente BibTeX para integración directa con gestores de referencias.
"""

import argparse
import json
import os
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


def build_query(args: argparse.Namespace) -> str:
    """Construye la cadena de búsqueda con filtros aplicados."""
    parts = [args.query]

    if args.author:
        parts.append(f"author:{args.author}")
    if args.title_contains:
        parts.append(f"intitle:{args.title_contains}")

    return " ".join(parts)


def search_exa(args: argparse.Namespace) -> dict[str, Any]:
    """Ejecuta la búsqueda en EXA y retorna resultados estructurados."""
    exa = Exa(EXA_API_KEY)
    query_str = build_query(args)

    search_params: dict[str, Any] = {
        "num_results": args.limit,
        "category": "research paper",
        "text": True,
    }

    if args.start_year:
        search_params["start_published_date"] = f"{args.start_year}-01-01"
    if args.end_year:
        search_params["end_published_date"] = f"{args.end_year}-12-31"
    if args.domains:
        search_params["include_domains"] = [
            d.strip() for d in args.domains.split(",")
        ]

    print(f"Buscando en EXA: {query_str}", file=sys.stderr)
    print(f"Filtros: {search_params}", file=sys.stderr)

    try:
        response = exa.search_and_contents(query_str, **search_params)
    except Exception as e:
        print(f"Error en la búsqueda EXA: {e}", file=sys.stderr)
        sys.exit(1)

    return format_results(args, query_str, response.results)


def format_results(
    args: argparse.Namespace, query_str: str, results: list[Any]
) -> dict[str, Any]:
    """Formatea los resultados en la estructura estándar del skill."""

    formatted: list[dict[str, Any]] = []
    for r in results:
        entry: dict[str, Any] = {
            "title": getattr(r, "title", None) or "Sin título",
            "authors": getattr(r, "author", None) or [],
            "year": _extract_year(r),
            "doi": None,
            "url": getattr(r, "url", None) or "",
            "source": "exa",
        }

        if not isinstance(entry["authors"], list):
            entry["authors"] = [entry["authors"]] if entry["authors"] else []

        # Extraer DOI de la URL si está presente
        url = entry["url"]
        if url and "doi.org/" in url:
            entry["doi"] = url.split("doi.org/")[-1]

        # Texto del artículo (abstract o snippet)
        text = getattr(r, "text", None)
        if text:
            # Tomar primeras 500 chars como resumen
            entry["abstract"] = text[:500]

        formatted.append(entry)

    return {
        "query": query_str,
        "timestamp": datetime.now().isoformat(),
        "sources_used": ["exa"],
        "total_results": len(formatted),
        "results": formatted,
    }


def _extract_year(result: Any) -> int | None:
    """Extrae el año de publicación del resultado de EXA."""
    published = getattr(result, "published_date", None)
    if published:
        try:
            return int(published[:4])
        except (ValueError, TypeError):
            pass
    return None


def to_bibtex(results: dict[str, Any]) -> str:
    """Convierte los resultados a formato BibTeX con claves únicas."""
    entries: list[str] = []
    used_keys: set[str] = set()

    for i, r in enumerate(results["results"]):
        cite_key = _make_cite_key(r, i)
        # Desambiguar si la clave ya existe
        if cite_key in used_keys:
            suffix = ord("a")
            while f"{cite_key}{chr(suffix)}" in used_keys:
                suffix += 1
            cite_key = f"{cite_key}{chr(suffix)}"
        used_keys.add(cite_key)

        entry_type = "article"

        lines = [f"@{entry_type}{{{cite_key},"]
        lines.append(f"  title = {{{r.get('title', '')}}},")

        authors = r.get("authors", [])
        if authors:
            authors_str = " and ".join(authors)
            lines.append(f"  author = {{{authors_str}}},")

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
    """Genera una clave de cita BibTeX a partir de autor y año."""
    authors = result.get("authors", [])
    year = result.get("year", "????")

    if authors:
        last_name = authors[0].split()[-1].lower().replace(",", "")
        return f"{last_name}{year}"
    return f"ref{index + 1}{year}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Busca artículos académicos usando la API de EXA.",
        epilog="Requiere EXA_API_KEY en variable de entorno.",
    )
    parser.add_argument("query", help="Tema o frase de búsqueda")
    parser.add_argument(
        "--start-year",
        type=int,
        help="Año inicial del rango de publicación (inclusive)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        help="Año final del rango de publicación (inclusive)",
    )
    parser.add_argument(
        "--domains",
        help="Dominios a incluir, separados por coma (ej: arxiv.org,dl.acm.org)",
    )
    parser.add_argument(
        "--author",
        help="Filtrar por autor específico",
    )
    parser.add_argument(
        "--title-contains",
        help="Filtrar por palabras en el título",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Número máximo de resultados (default: 10)",
    )
    parser.add_argument(
        "--output",
        help="Archivo de salida (si no se especifica, imprime a stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "bibtex"],
        default="json",
        help="Formato de salida (default: json)",
    )
    args = parser.parse_args()

    results = search_exa(args)

    if args.format == "bibtex":
        output_str = to_bibtex(results)
    else:
        output_str = json.dumps(results, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)
        print(f"Resultados guardados en {args.output}", file=sys.stderr)
    else:
        print(output_str)


if __name__ == "__main__":
    main()
