#!/usr/bin/env python3
"""
Combina y deduplica resultados de múltiples búsquedas académicas.

Toma dos o más archivos JSON producidos por search_exa.py y/o
search_semantic_scholar.py, y produce un archivo unificado con:
  - Deduplicación por DOI exacto
  - Deduplicación por similitud difusa de título (umbral ≥ 0.85)
  - Conservación de la entrada con más metadatos en caso de conflicto
  - Marcado de fuentes múltiples con campo also_found_in

Uso:
  python scripts/merge_results.py exa.json semantic.json --output unified.json
  python scripts/merge_results.py *.json --output todo.json --format bibtex
"""

import argparse
import json
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any


def load_json(path: str) -> dict[str, Any]:
    """Carga un archivo JSON de resultados de búsqueda."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "results" not in data:
        print(
            f"Advertencia: {path} no tiene campo 'results'. Se omite.",
            file=sys.stderr,
        )
        return {"results": [], "sources_used": []}

    return data


def normalize_title(title: str) -> str:
    """Normaliza un título para comparación: minúsculas, sin puntuación."""
    title = title.lower()
    title = re.sub(r"[^a-záéíóúñ0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def title_similarity(a: str, b: str) -> float:
    """Calcula la similitud difusa entre dos títulos normalizados."""
    a_norm = normalize_title(a)
    b_norm = normalize_title(b)
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def count_metadata_fields(entry: dict[str, Any]) -> int:
    """Cuenta cuántos campos con valor no nulo tiene una entrada."""
    fields = [
        "doi",
        "abstract",
        "citation_count",
        "venue",
        "journal",
        "fields_of_study",
        "open_access_pdf",
    ]
    return sum(1 for f in fields if entry.get(f))


def merge_results(
    inputs: list[str], threshold: float = 0.85
) -> dict[str, Any]:
    """
    Carga, combina y deduplica resultados de múltiples archivos JSON.

    Algoritmo:
      1. Cargar todos los archivos y aplanar sus results[].
      2. Primera pasada: agrupar por DOI exacto (si existe).
      3. Segunda pasada: agrupar entradas sin DOI por similitud de título.
      4. Para cada grupo, conservar la entrada con más metadatos.
      5. Marcar also_found_in con las fuentes adicionales.
    """
    all_results: list[dict[str, Any]] = []
    all_sources: set[str] = set()
    query_parts: list[str] = []

    for path in inputs:
        data = load_json(path)
        all_results.extend(data.get("results", []))
        all_sources.update(data.get("sources_used", []))
        q = data.get("query", "")
        if q:
            query_parts.append(q)

    # --- Pasada 1: deduplicar por DOI ---
    by_doi: dict[str, dict[str, Any]] = {}
    without_doi: list[dict[str, Any]] = []

    for entry in all_results:
        doi = entry.get("doi")
        if doi:
            doi = doi.strip().lower()
            if doi in by_doi:
                existing = by_doi[doi]
                # Conservar la entrada con más metadatos
                if count_metadata_fields(entry) > count_metadata_fields(
                    existing
                ):
                    entry.setdefault("also_found_in", []).append(
                        existing.get("source", "unknown")
                    )
                    # Migrar also_found_in de la entrada anterior
                    prev_also = existing.get("also_found_in", [])
                    prev_source = existing.get("source")
                    if prev_source and prev_source not in prev_also:
                        prev_also.append(prev_source)
                    entry.setdefault("also_found_in", []).extend(prev_also)
                    by_doi[doi] = entry
                else:
                    existing.setdefault("also_found_in", []).append(
                        entry.get("source", "unknown")
                    )
            else:
                by_doi[doi] = entry
        else:
            without_doi.append(entry)

    merged: list[dict[str, Any]] = list(by_doi.values())

    # --- Pasada 2: deduplicar entradas sin DOI por título ---
    unmatched: list[dict[str, Any]] = []
    for entry in without_doi:
        title = entry.get("title", "")
        found = False
        for existing in merged:
            existing_title = existing.get("title", "")
            sim = title_similarity(title, existing_title)
            if sim >= threshold:
                # Es un duplicado probable
                if count_metadata_fields(entry) > count_metadata_fields(
                    existing
                ):
                    merged.remove(existing)
                    entry.setdefault("also_found_in", []).append(
                        existing.get("source", "unknown")
                    )
                    merged.append(entry)
                else:
                    existing.setdefault("also_found_in", []).append(
                        entry.get("source", "unknown")
                    )
                found = True
                break
        if not found:
            unmatched.append(entry)

    merged.extend(unmatched)

    return {
        "query": " | ".join(query_parts),
        "timestamp": datetime.now().isoformat(),
        "sources_used": sorted(all_sources),
        "total_results": len(merged),
        "deduplicated": len(all_results) - len(merged),
        "results": merged,
    }


def to_bibtex(results: dict[str, Any]) -> str:
    """Convierte los resultados unificados a formato BibTeX con claves únicas."""
    entries: list[str] = []
    used_keys: set[str] = set()

    for i, r in enumerate(results["results"]):
        authors = r.get("authors", [])
        year = r.get("year", "????")

        if authors:
            last_name = authors[0].split()[-1].lower().replace(",", "")
            cite_key = f"{last_name}{year}"
        else:
            cite_key = f"ref{i + 1}{year}"

        # Agregar letra de desambiguación si hay colisión
        if cite_key in used_keys:
            suffix = ord("a")
            while f"{cite_key}{chr(suffix)}" in used_keys:
                suffix += 1
            cite_key = f"{cite_key}{chr(suffix)}"
        used_keys.add(cite_key)

        entry_type = "article"
        lines = [f"@{entry_type}{{{cite_key},"]
        lines.append(f"  title = {{{r.get('title', '')}}},")

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Combina y deduplica resultados de búsquedas académicas.",
        epilog=(
            "Acepta archivos JSON de search_exa.py y search_semantic_scholar.py. "
            "Deduplica por DOI exacto y por similitud difusa de título."
        ),
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Archivos JSON de resultados a combinar (2 o más)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Archivo de salida unificado",
    )
    parser.add_argument(
        "--format",
        choices=["json", "bibtex"],
        default="json",
        help="Formato de salida (default: json)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Umbral de similitud para deduplicación por título (default: 0.85)",
    )
    args = parser.parse_args()

    if len(args.inputs) < 2:
        parser.error("Se requieren al menos 2 archivos de entrada")

    results = merge_results(args.inputs, args.threshold)

    if args.format == "bibtex":
        output_str = to_bibtex(results)
    else:
        output_str = json.dumps(results, indent=2, ensure_ascii=False)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(output_str)

    print(
        f"Resultados unificados: {results['total_results']} entradas "
        f"({results['deduplicated']} duplicados eliminados) → {args.output}",
        file=sys.stderr,
    )
    print(
        f"Fuentes combinadas: {', '.join(results['sources_used'])}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
