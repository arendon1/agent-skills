#!/usr/bin/env python3
"""
Busca artículos académicos usando la API REST de Semantic Scholar.

Usa los endpoints /paper/search y /paper/search/match para descubrir
artículos por palabra clave o por título. No requiere API key (rate limit
sin key: 100 req/5 min). Con SEMANTIC_SCHOLAR_API_KEY el límite sube a
100 req/seg.

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
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    print(
        "Error: requests no está instalado. Instalalo con: pip install requests",
        file=sys.stderr,
    )
    sys.exit(1)


BASE_URL = "https://api.semanticscholar.org/graph/v1"
API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

# Campos que pedimos a la API para cada paper
PAPER_FIELDS = [
    "title",
    "authors",
    "year",
    "venue",
    "publicationDate",
    "abstract",
    "externalIds",
    "url",
    "citationCount",
    "fieldsOfStudy",
    "journal",
    "openAccessPdf",
    "publicationTypes",
]


def _headers() -> dict[str, str]:
    """Construye los headers HTTP, incluyendo API key si está disponible."""
    h = {"Accept": "application/json"}
    if API_KEY:
        h["x-api-key"] = API_KEY
    return h


def search_by_keyword(args: argparse.Namespace) -> dict[str, Any]:
    """
    Busca artículos por palabra clave usando /paper/search.

    Aplica filtros opcionales: año, venue, campos de estudio,
    tipo de publicación, mínimo de citas.
    """
    params: dict[str, Any] = {
        "query": args.query,
        "limit": min(args.limit, 100),
        "fields": ",".join(PAPER_FIELDS),
    }

    if args.year:
        params["year"] = args.year
    if args.venue:
        params["venue"] = args.venue
    if args.fields_of_study:
        params["fieldsOfStudy"] = args.fields_of_study
    if args.publication_types:
        params["publicationTypes"] = args.publication_types
    if args.min_citations is not None:
        params["minCitationCount"] = args.min_citations

    url = f"{BASE_URL}/paper/search?{urlencode(params)}"
    print(f"Buscando en Semantic Scholar: {args.query}", file=sys.stderr)

    try:
        resp = requests.get(url, headers=_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error en la búsqueda Semantic Scholar: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None:
            print(f"Respuesta del servidor: {e.response.text[:500]}", file=sys.stderr)
        sys.exit(1)

    return data.get("data", [])


def search_by_title(args: argparse.Namespace) -> dict[str, Any]:
    """
    Busca artículos por coincidencia de título usando /paper/search/match.

    Útil para verificar si un paper específico existe en la base de datos.
    """
    params: dict[str, Any] = {
        "query": args.match,
        "fields": ",".join(PAPER_FIELDS),
    }

    url = f"{BASE_URL}/paper/search/match?{urlencode(params)}"
    print(f"Verificando título en Semantic Scholar: {args.match}", file=sys.stderr)

    try:
        resp = requests.get(url, headers=_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error en la verificación Semantic Scholar: {e}", file=sys.stderr)
        sys.exit(1)

    return data.get("data", [])


def format_results(
    query_str: str, raw_results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Formatea los resultados crudos de Semantic Scholar en la estructura estándar."""

    formatted: list[dict[str, Any]] = []
    for paper in raw_results:
        external_ids = paper.get("externalIds") or {}
        authors_list = paper.get("authors") or []

        entry: dict[str, Any] = {
            "title": paper.get("title") or "Sin título",
            "authors": [a.get("name", "Desconocido") for a in authors_list],
            "year": paper.get("year"),
            "doi": external_ids.get("DOI"),
            "url": paper.get("url") or "",
            "source": "semantic_scholar",
            "citation_count": paper.get("citationCount"),
        }

        # Agregar abstract si existe
        abstract = paper.get("abstract")
        if abstract:
            entry["abstract"] = abstract[:500]

        # Agregar venue / journal
        venue = paper.get("venue") or ""
        journal = paper.get("journal")
        if journal and isinstance(journal, dict):
            journal_name = journal.get("name", "")
            if journal_name:
                entry["journal"] = journal_name
        elif venue:
            entry["venue"] = venue

        # Agregar campos de estudio
        fields = paper.get("fieldsOfStudy")
        if fields:
            entry["fields_of_study"] = fields

        # Agregar PDF de acceso abierto si existe
        open_access = paper.get("openAccessPdf")
        if open_access and isinstance(open_access, dict):
            entry["open_access_pdf"] = open_access.get("url")

        formatted.append(entry)

    return {
        "query": query_str,
        "timestamp": datetime.now().isoformat(),
        "sources_used": ["semantic_scholar"],
        "total_results": len(formatted),
        "results": formatted,
    }


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
        if r.get("journal"):
            lines.append(f"  journal = {{{r['journal']}}},")

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
        description="Busca artículos académicos usando la API de Semantic Scholar.",
        epilog=(
            "Sin API key: 100 req/5 min. Con SEMANTIC_SCHOLAR_API_KEY: 100 req/seg. "
            "Documentación: https://api.semanticscholar.org/graph/v1/swagger.json"
        ),
    )

    # Modo de búsqueda: keyword (default) o match (título)
    parser.add_argument(
        "query",
        nargs="?",
        help="Tema o frase de búsqueda por palabra clave (modo por defecto)",
    )
    parser.add_argument(
        "--match",
        help="Buscar por coincidencia exacta de título (usa /paper/search/match)",
    )
    parser.add_argument(
        "--year",
        help="Rango de años (ej: 2020-2025 o año único 2024)",
    )
    parser.add_argument(
        "--venue",
        help="Filtrar por venue (ej: 'Nature|Science'). Usa | para múltiples valores.",
    )
    parser.add_argument(
        "--fields-of-study",
        help="Campos de estudio (ej: 'Computer Science|Medicine')",
    )
    parser.add_argument(
        "--publication-types",
        help="Tipos de publicación (ej: 'JournalArticle|Review|Conference')",
    )
    parser.add_argument(
        "--min-citations",
        type=int,
        help="Número mínimo de citas",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Número máximo de resultados (default: 10, max: 100)",
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

    # Determinar modo de búsqueda
    if args.match:
        raw_results = search_by_title(args)
        query_str = f"title:{args.match}"
    elif args.query:
        raw_results = search_by_keyword(args)
        query_str = args.query
    else:
        parser.error("Debe especificar query o --match")

    results = format_results(query_str, raw_results)

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
