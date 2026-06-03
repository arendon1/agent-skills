"""
Fetch and merge LLM model data from OpenRouter and Artificial Analysis.

Usage:
    python scripts/fetch_models.py --output catalog.json
    python scripts/fetch_models.py --or-only --output catalog.json
    python scripts/fetch_models.py --aa-only --output catalog.json

Output: unified JSON array of model objects.
See SKILL.md for the full output schema.
"""

import sys
import json
import argparse
from pathlib import Path

# Allow running from the skill root directory
sys.path.insert(0, str(Path(__file__).parent))

from client_openrouter import fetch_models as _fetch_or
from client_aa import fetch_llm_models as _fetch_aa


def _normalize(text: str) -> str:
    """Lowercase and strip for fuzzy name matching."""
    return text.lower().strip()


def _build_aa_lookup(aa_models: list[dict]) -> dict:
    """
    Build a lookup dict for fast matching against OpenRouter model names.
    Indexes by: normalized name, slug, and common sub-slug variants.
    """
    lookup: dict[str, dict] = {}
    for m in aa_models:
        for key in [m.get("name", ""), m.get("slug", "")]:
            if key:
                lookup[_normalize(key)] = m
        # Also index by model_creator+name combo (e.g. "openai/o3-mini" -> "o3-mini")
        slug = m.get("slug", "")
        if "-" in slug:
            parts = slug.split("-")
            # Try both the full slug and partial slugs for flexibility
            for i in range(1, len(parts)):
                partial = "-".join(parts[i:])
                if partial not in lookup:
                    lookup[partial] = m
    return lookup


def merge_models(or_models: list[dict], aa_models: list[dict]) -> list[dict]:
    """
    Merge OpenRouter and Artificial Analysis model data.

    Matching strategy (in order):
    1. Exact normalized name match
    2. OR model slug (last segment of `provider/slug`) vs AA name/slug
    3. Partial slug matching

    Returns unified model list; unmatched models include only OR data.
    """
    aa_lookup = _build_aa_lookup(aa_models)
    merged = []

    for or_model in or_models:
        model_id: str = or_model.get("id", "")
        name: str = or_model.get("name", "")
        # Slug = last part of "provider/model-name"
        slug = model_id.split("/")[-1] if "/" in model_id else model_id

        aa_data = (
            aa_lookup.get(_normalize(name))
            or aa_lookup.get(_normalize(slug))
        )

        entry: dict = {
            "id": model_id,
            "name": name,
            "context_length": or_model.get("context_length"),
            "pricing": or_model.get("pricing", {}),
            "top_provider": or_model.get("top_provider", {}),
            "supported_parameters": or_model.get("supported_parameters", []),
            "architecture": or_model.get("architecture", {}),
        }

        if aa_data:
            entry["aa"] = {
                "id": aa_data.get("id"),
                "slug": aa_data.get("slug"),
                "model_creator": aa_data.get("model_creator", {}),
                "evaluations": aa_data.get("evaluations", {}),
                "pricing_aa": aa_data.get("pricing", {}),
                "median_output_tokens_per_second": aa_data.get("median_output_tokens_per_second"),
                "median_time_to_first_token_seconds": aa_data.get("median_time_to_first_token_seconds"),
                "median_time_to_first_answer_token": aa_data.get("median_time_to_first_answer_token"),
            }

        merged.append(entry)

    return merged


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and merge LLM model data from OpenRouter + Artificial Analysis"
    )
    parser.add_argument("--output", "-o", default=None, help="Output JSON file path (default: stdout)")
    parser.add_argument("--or-only", action="store_true", help="Only fetch OpenRouter data")
    parser.add_argument("--aa-only", action="store_true", help="Only fetch Artificial Analysis data")
    args = parser.parse_args()

    if args.or_only:
        print("Fetching OpenRouter models...")
        models = _fetch_or()
        print(f"  {len(models)} models fetched")

    elif args.aa_only:
        print("Fetching Artificial Analysis models...")
        models = _fetch_aa()
        print(f"  {len(models)} models fetched")

    else:
        print("Fetching OpenRouter models...")
        or_models = _fetch_or()
        print(f"  {len(or_models)} models")

        print("Fetching Artificial Analysis models...")
        aa_models = _fetch_aa()
        print(f"  {len(aa_models)} models")

        print("Merging datasets...")
        models = merge_models(or_models, aa_models)
        enriched = sum(1 for m in models if "aa" in m)
        print(f"  {len(models)} total models ({enriched} enriched with AA benchmarks, {len(models) - enriched} OR-only)")

    output = json.dumps(models, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Catalog saved to: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
