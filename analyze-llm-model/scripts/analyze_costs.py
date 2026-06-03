"""
Cost analysis engine for LLM usage logs.

Accepts a usage log (JSON or CSV) and a model catalog produced by fetch_models.py,
then produces a detailed cost breakdown per model.

Usage:
    python scripts/analyze_costs.py usage.json --catalog catalog.json
    python scripts/analyze_costs.py usage.csv  --catalog catalog.json --output report.json

Usage log format: see references/usage-format.md
"""

import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_usage_json(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    # Support {"data": [...]} envelope
    if isinstance(raw, dict) and "data" in raw:
        return raw["data"]
    raise ValueError(f"Unexpected JSON structure in {path}. Expected array or {{\"data\": [...]}}")


def _load_usage_csv(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "timestamp": row.get("timestamp", ""),
                "model_id": row.get("model_id", ""),
                "input_tokens": int(row.get("input_tokens", 0) or 0),
                "output_tokens": int(row.get("output_tokens", 0) or 0),
                "session_id": row.get("session_id", ""),
                "task_id": row.get("task_id", ""),
            })
    return rows


def load_usage(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Usage file not found: {path}")
    if p.suffix.lower() == ".csv":
        return _load_usage_csv(p)
    return _load_usage_json(p)


def load_catalog(catalog_path: str) -> dict[str, dict]:
    """Load model catalog as a dict keyed by model_id."""
    p = Path(catalog_path)
    if not p.exists():
        raise FileNotFoundError(
            f"Catalog not found: {catalog_path}\n"
            "Run 'python scripts/fetch_models.py --output catalog.json' first."
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {m["id"]: m for m in data}
    raise ValueError("Catalog must be a JSON array of model objects.")


# ---------------------------------------------------------------------------
# Aliases and subscriptions
# ---------------------------------------------------------------------------

def load_aliases() -> dict[str, str]:
    aliases_path = Path(__file__).resolve().parent.parent / "references" / "aliases.json"
    if not aliases_path.exists():
        return {}
    data = json.loads(aliases_path.read_text(encoding="utf-8"))
    return data.get("mappings", {})


def _provider_for_model(model_id: str) -> str:
    if model_id.startswith("opencode-go/"):
        return "opencode-go"
    if model_id.startswith("github-copilot/"):
        return "github-copilot"
    return ""


def load_subscriptions() -> dict | None:
    subs_path = Path(__file__).resolve().parent.parent / "references" / "subscriptions.json"
    if not subs_path.exists():
        return None
    return json.loads(subs_path.read_text(encoding="utf-8"))


def _compute_efficiency(by_model: dict, catalog: dict[str, dict], aliases: dict[str, str]) -> list[dict]:
    subs = load_subscriptions()
    if not subs:
        return []

    providers = subs.get("providers", {})
    results = []

    for prov_id, prov_info in providers.items():
        prov_type = prov_info.get("type", "api_only")
        if prov_type == "api_only":
            continue

        prov_input = 0
        prov_output = 0
        for model_id, stats in by_model.items():
            if _provider_for_model(model_id) == prov_id:
                prov_input += stats["input_tokens"]
                prov_output += stats["output_tokens"]

        if prov_input == 0 and prov_output == 0:
            continue

        or_cost = 0.0
        for model_id, stats in by_model.items():
            if _provider_for_model(model_id) != prov_id:
                continue
            resolved = aliases.get(model_id, model_id)
            model = catalog.get(resolved)
            if model:
                pricing = model.get("pricing", {})
                prompt_price = float(pricing.get("prompt", 0) or 0)
                completion_price = float(pricing.get("completion", 0) or 0)
                or_cost += stats["input_tokens"] * prompt_price + stats["output_tokens"] * completion_price

        if prov_type == "token_budget":
            tiers = prov_info.get("tiers", [])
            for tier in tiers:
                monthly = tier.get("price_monthly_usd", 0)
                if monthly <= 0:
                    continue
                ratio = or_cost / monthly
                results.append({
                    "provider": prov_id,
                    "tier": tier["name"],
                    "price_monthly_usd": monthly,
                    "type": prov_type,
                    "tokens_input": prov_input,
                    "tokens_output": prov_output,
                    "openrouter_equivalent_usd": round(or_cost, 4),
                    "savings_usd": round(or_cost - monthly, 4),
                    "efficiency_ratio": round(ratio, 2),
                })
        elif prov_type == "rate_access":
            results.append({
                "provider": prov_id,
                "type": prov_type,
                "tiers": prov_info.get("tiers", []),
                "tokens_input": prov_input,
                "tokens_output": prov_output,
                "openrouter_equivalent_usd": round(or_cost, 4),
                "note": "Rate-access subscription — provides usage limits and model access, not a token budget. Direct cost comparison not applicable."
            })

    return results


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------

def _model_cost(model: dict, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate USD cost for a single API call.
    Pricing values from OpenRouter are USD per token (not per million).
    """
    pricing = model.get("pricing", {})
    prompt_price = float(pricing.get("prompt", 0) or 0)
    completion_price = float(pricing.get("completion", 0) or 0)
    return (input_tokens * prompt_price) + (output_tokens * completion_price)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(usage: list[dict], catalog: dict[str, dict]) -> dict:
    """
    Compute cost breakdown from usage log against the model catalog.

    Returns a report dict with:
    - summary: totals across all models
    - by_model: per-model breakdown sorted by total cost (descending)
    - unknown_models: model IDs that appeared in usage but not in catalog
    """
    by_model: dict[str, dict] = defaultdict(lambda: {
        "calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_cost": 0.0,
    })
    unknown_models: set[str] = set()

    aliases = load_aliases()

    for entry in usage:
        model_id: str = entry.get("model_id", "unknown")
        resolved_id = aliases.get(model_id, model_id)
        model = catalog.get(resolved_id)
        inp = int(entry.get("input_tokens", 0) or 0)
        out = int(entry.get("output_tokens", 0) or 0)

        cost = 0.0
        if model:
            cost = _model_cost(model, inp, out)
        else:
            unknown_models.add(model_id)

        stats = by_model[model_id]
        stats["calls"] += 1
        stats["input_tokens"] += inp
        stats["output_tokens"] += out
        stats["total_cost"] += cost
        stats["resolved_id"] = resolved_id

    total_cost = sum(v["total_cost"] for v in by_model.values())
    total_calls = sum(v["calls"] for v in by_model.values())
    total_input = sum(v["input_tokens"] for v in by_model.values())
    total_output = sum(v["output_tokens"] for v in by_model.values())

    sorted_models = sorted(by_model.items(), key=lambda x: x[1]["total_cost"], reverse=True)

    return {
        "summary": {
            "total_cost_usd": round(total_cost, 6),
            "total_calls": total_calls,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "avg_cost_per_call_usd": round(total_cost / total_calls, 6) if total_calls else 0.0,
            "avg_input_tokens_per_call": round(total_input / total_calls, 1) if total_calls else 0.0,
            "avg_output_tokens_per_call": round(total_output / total_calls, 1) if total_calls else 0.0,
        },
        "by_model": [
            {
                "model_id": model_id,
                "resolved_model_id": stats.get("resolved_id", model_id),
                "name": catalog.get(stats.get("resolved_id", model_id), {}).get("name", model_id),
                "calls": stats["calls"],
                "input_tokens": stats["input_tokens"],
                "output_tokens": stats["output_tokens"],
                "total_cost_usd": round(stats["total_cost"], 6),
                "cost_share_pct": round(stats["total_cost"] / total_cost * 100, 2) if total_cost else 0.0,
                "avg_cost_per_call_usd": round(stats["total_cost"] / stats["calls"], 6) if stats["calls"] else 0.0,
                "intelligence_index": (
                    catalog.get(stats.get("resolved_id", model_id), {})
                    .get("aa", {})
                    .get("evaluations", {})
                    .get("artificial_analysis_intelligence_index")
                ),
                "tokens_per_second": (
                    catalog.get(stats.get("resolved_id", model_id), {})
                    .get("aa", {})
                    .get("median_output_tokens_per_second")
                ),
            }
            for model_id, stats in sorted_models
        ],
        "unknown_models": sorted(unknown_models),
        "subscription_efficiency": _compute_efficiency(by_model, catalog, aliases),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_report(report: dict) -> None:
    s = report["summary"]
    print("\n=== Cost Analysis Summary ===")
    print(f"  Total cost     : ${s['total_cost_usd']:.4f} USD")
    print(f"  Total calls    : {s['total_calls']:,}")
    print(f"  Total tokens   : {s['total_input_tokens'] + s['total_output_tokens']:,}")
    print(f"  Avg cost/call  : ${s['avg_cost_per_call_usd']:.6f} USD")
    print(f"  Avg in/out     : {s['avg_input_tokens_per_call']:.0f} / {s['avg_output_tokens_per_call']:.0f} tokens")

    print("\nTop models by spend:")
    for m in report["by_model"][:8]:
        intel = f"  IQ:{m['intelligence_index']:.1f}" if m["intelligence_index"] else ""
        tps = f"  {m['tokens_per_second']:.0f}tok/s" if m["tokens_per_second"] else ""
        print(
            f"  {m['model_id']:<45} "
            f"${m['total_cost_usd']:.4f}  "
            f"({m['cost_share_pct']:.1f}%)"
            f"{intel}{tps}"
        )

    if report["unknown_models"]:
        print(f"\nWarning: {len(report['unknown_models'])} model(s) not found in catalog (no pricing):")
        for mid in report["unknown_models"]:
            print(f"  - {mid}")
        print("  Tip: re-run fetch_models.py to refresh the catalog.")

    if report.get("subscription_efficiency"):
        print("\n=== Subscription Efficiency ===")
        for se in report["subscription_efficiency"]:
            if se["type"] == "token_budget":
                ratio_str = f"{se['efficiency_ratio']}x"
                print(
                    f"\n  {se['provider']} / {se['tier']} tier "
                    f"(${se['price_monthly_usd']:.2f}/mo):"
                )
                print(f"    Tokens: {se['tokens_input']:,} in / {se['tokens_output']:,} out")
                print(f"    OpenRouter equivalent: ${se['openrouter_equivalent_usd']:.4f} USD")
                savings = se["savings_usd"]
                if savings > 0:
                    print(f"    Savings: ${savings:.4f} USD  |  Efficiency ratio: {ratio_str}")
                elif savings < 0:
                    print(f"    Overspend: ${-savings:.4f} USD  |  Efficiency ratio: {ratio_str}")
                else:
                    print(f"    Break-even  |  Efficiency ratio: {ratio_str}")
            elif se["type"] == "rate_access":
                tier_names = ", ".join(
                    f"{t['name']} (${t.get('price_monthly_usd', 0)}/mo)"
                    for t in se.get("tiers", [])
                )
                print(f"\n  {se['provider']}:")
                print(f"    {se['note']}")
                print(f"    Tokens: {se['tokens_input']:,} in / {se['tokens_output']:,} out")
                print(f"    OpenRouter equivalent: ${se['openrouter_equivalent_usd']:.4f} USD")
                print(f"    Available tiers: {tier_names}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze LLM usage costs")
    parser.add_argument("usage", help="Usage log file (.json or .csv)")
    parser.add_argument("--catalog", "-c", required=True, help="Model catalog JSON (from fetch_models.py)")
    parser.add_argument("--output", "-o", default=None, help="Save JSON report to this path")
    args = parser.parse_args()

    usage = load_usage(args.usage)
    catalog = load_catalog(args.catalog)
    report = analyze(usage, catalog)

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report saved to: {args.output}")

    _print_report(report)


if __name__ == "__main__":
    main()
