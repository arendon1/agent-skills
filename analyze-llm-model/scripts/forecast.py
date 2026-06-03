"""
Usage forecasting for LLM costs.

Uses linear-trend extrapolation over historical daily usage to project future
spend per model. Also finds cheaper model alternatives for top-cost models.

Usage:
    python scripts/forecast.py usage.json --catalog catalog.json --days 30
    python scripts/forecast.py usage.csv  --catalog catalog.json --days 90 --output forecast.json

Usage log format: see references/usage-format.md
"""

import csv
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional


# ---------------------------------------------------------------------------
# Loaders (duplicated from analyze_costs.py for standalone use)
# ---------------------------------------------------------------------------

def _load_usage_json(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "data" in raw:
        return raw["data"]
    raise ValueError(f"Unexpected JSON structure in {path}.")


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
            })
    return rows


def _load_usage(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Usage file not found: {path}")
    return _load_usage_csv(p) if p.suffix.lower() == ".csv" else _load_usage_json(p)


def _load_catalog(catalog_path: str) -> list[dict]:
    p = Path(catalog_path)
    if not p.exists():
        raise FileNotFoundError(
            f"Catalog not found: {catalog_path}\n"
            "Run 'python scripts/fetch_models.py --output catalog.json' first."
        )
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Aliases and subscriptions
# ---------------------------------------------------------------------------

def _load_aliases() -> dict[str, str]:
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


def _load_subscriptions() -> dict | None:
    subs_path = Path(__file__).resolve().parent.parent / "references" / "subscriptions.json"
    if not subs_path.exists():
        return None
    return json.loads(subs_path.read_text(encoding="utf-8"))


def _compute_efficiency(by_model: dict, catalog: dict[str, dict], aliases: dict[str, str]) -> list[dict]:
    subs = _load_subscriptions()
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
# Temporal aggregation
# ---------------------------------------------------------------------------

_TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def _parse_ts(ts: str) -> Optional[datetime]:
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return None


def _daily_totals(usage: list[dict]) -> dict[str, dict]:
    """Aggregate usage into daily buckets."""
    daily: dict[str, dict] = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0})
    for entry in usage:
        ts = _parse_ts(entry.get("timestamp", ""))
        if not ts:
            continue
        day = ts.strftime("%Y-%m-%d")
        daily[day]["calls"] += 1
        daily[day]["input_tokens"] += int(entry.get("input_tokens", 0) or 0)
        daily[day]["output_tokens"] += int(entry.get("output_tokens", 0) or 0)
    return dict(daily)


# ---------------------------------------------------------------------------
# Linear trend
# ---------------------------------------------------------------------------

def _linear_regression(values: list[float]) -> tuple[float, float]:
    """
    Simple OLS linear regression on evenly-spaced index [0, n-1].
    Returns (slope, intercept).
    """
    n = len(values)
    if n < 2:
        return 0.0, float(values[0]) if values else 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0.0
    intercept = y_mean - slope * x_mean
    return slope, intercept


def _project(slope: float, intercept: float, n_hist: int, horizon_days: int) -> float:
    """
    Project the average daily value at the midpoint of the forecast window,
    then multiply by horizon_days. Clamps to zero.
    """
    mid = n_hist + horizon_days / 2.0
    projected_daily = slope * mid + intercept
    return max(0.0, projected_daily) * horizon_days


# ---------------------------------------------------------------------------
# Alternatives finder
# ---------------------------------------------------------------------------

def _blend_cost(model: dict) -> float:
    """Approximate blended cost per token using a 3:1 input:output ratio."""
    pricing = model.get("pricing", {})
    p = float(pricing.get("prompt", 0) or 0)
    c = float(pricing.get("completion", 0) or 0)
    return p * 0.75 + c * 0.25


def _find_alternatives(
    top_models: list[dict],
    catalog: list[dict],
    catalog_dict: dict[str, dict],
) -> list[dict]:
    """
    For each of the top 3 cost models, find up to 3 cheaper alternatives with:
    - Blend cost < 50% of target model blend cost
    - Context length >= 80% of target
    - Include AA intelligence index when available
    """
    alternatives = []

    for target_info in top_models[:3]:
        target_id = target_info["model_id"]
        target = catalog_dict.get(target_id)
        if not target:
            continue

        target_blend = _blend_cost(target)
        if target_blend == 0:
            continue
        target_ctx = target.get("context_length") or 0

        cheaper = []
        for candidate in catalog:
            if candidate["id"] == target_id:
                continue
            cand_blend = _blend_cost(candidate)
            cand_ctx = candidate.get("context_length") or 0

            if cand_blend <= 0 or cand_blend >= target_blend * 0.5:
                continue
            if target_ctx > 0 and cand_ctx < target_ctx * 0.8:
                continue

            savings_pct = (1.0 - cand_blend / target_blend) * 100
            potential_savings_usd = target_info["projected_cost_usd"] * (1.0 - cand_blend / target_blend)

            aa = candidate.get("aa", {})
            evals = aa.get("evaluations", {}) if aa else {}
            intelligence = evals.get("artificial_analysis_intelligence_index")
            speed = aa.get("median_output_tokens_per_second") if aa else None

            cheaper.append({
                "model_id": candidate["id"],
                "name": candidate.get("name", candidate["id"]),
                "context_length": cand_ctx,
                "savings_pct": round(savings_pct, 1),
                "potential_savings_usd": round(potential_savings_usd, 4),
                "intelligence_index": intelligence,
                "tokens_per_second": speed,
            })

        # Sort: highest savings first, break ties by intelligence (desc)
        cheaper.sort(key=lambda x: (-x["savings_pct"], -(x["intelligence_index"] or 0)))

        if cheaper:
            alternatives.append({
                "for_model": target_id,
                "projected_cost_usd": target_info["projected_cost_usd"],
                "cheaper_options": cheaper[:3],
            })

    return alternatives


# ---------------------------------------------------------------------------
# Main forecast engine
# ---------------------------------------------------------------------------

def forecast(usage_path: str, catalog_path: str, horizon_days: int = 30) -> dict:
    usage = _load_usage(usage_path)
    catalog = _load_catalog(catalog_path)
    catalog_dict = {m["id"]: m for m in catalog}

    # --- Temporal aggregation ---
    daily = _daily_totals(usage)
    if not daily:
        return {"error": "No timestamped entries found in usage log."}

    days = sorted(daily.keys())
    n = len(days)
    daily_calls = [daily[d]["calls"] for d in days]
    daily_input = [daily[d]["input_tokens"] for d in days]
    daily_output = [daily[d]["output_tokens"] for d in days]

    # --- Trend extrapolation ---
    call_s, call_i = _linear_regression(daily_calls)
    input_s, input_i = _linear_regression(daily_input)
    output_s, output_i = _linear_regression(daily_output)

    proj_calls = _project(call_s, call_i, n, horizon_days)
    proj_input = _project(input_s, input_i, n, horizon_days)
    proj_output = _project(output_s, output_i, n, horizon_days)

    # --- Per-model usage share from history ---
    model_hist: dict[str, dict] = defaultdict(lambda: {"calls": 0, "input": 0, "output": 0})
    for entry in usage:
        mid = entry.get("model_id", "unknown")
        model_hist[mid]["calls"] += 1
        model_hist[mid]["input"] += int(entry.get("input_tokens", 0) or 0)
        model_hist[mid]["output"] += int(entry.get("output_tokens", 0) or 0)

    total_hist_calls = sum(v["calls"] for v in model_hist.values())

    model_forecasts = []
    total_proj_cost = 0.0

    aliases = _load_aliases()

    for model_id, hist in sorted(model_hist.items(), key=lambda x: -x[1]["calls"]):
        resolved_id = aliases.get(model_id, model_id)
        model = catalog_dict.get(resolved_id, {})
        pricing = model.get("pricing", {})
        prompt_price = float(pricing.get("prompt", 0) or 0)
        completion_price = float(pricing.get("completion", 0) or 0)

        share = hist["calls"] / total_hist_calls if total_hist_calls else 0.0
        proj_model_input = proj_input * share
        proj_model_output = proj_output * share
        proj_cost = proj_model_input * prompt_price + proj_model_output * completion_price

        total_proj_cost += proj_cost

        aa = model.get("aa", {}) if model else {}
        evals = aa.get("evaluations", {}) if aa else {}

        model_forecasts.append({
            "model_id": model_id,
            "name": model.get("name", model_id) if model else model_id,
            "historical_calls": hist["calls"],
            "usage_share_pct": round(share * 100, 1),
            "projected_input_tokens": round(proj_model_input),
            "projected_output_tokens": round(proj_model_output),
            "projected_cost_usd": round(proj_cost, 4),
            "intelligence_index": evals.get("artificial_analysis_intelligence_index"),
        })

    # Sort by projected cost descending
    model_forecasts.sort(key=lambda x: -x["projected_cost_usd"])

    # --- Alternatives ---
    alternatives = _find_alternatives(model_forecasts, catalog, catalog_dict)

    proj_by_model = {
        mf["model_id"]: {
            "input_tokens": mf["projected_input_tokens"],
            "output_tokens": mf["projected_output_tokens"],
        }
        for mf in model_forecasts
    }

    return {
        "horizon_days": horizon_days,
        "historical_period": {
            "start": days[0],
            "end": days[-1],
            "days_with_data": n,
        },
        "projected_total_cost_usd": round(total_proj_cost, 4),
        "projected_calls": round(proj_calls),
        "projected_input_tokens": round(proj_input),
        "projected_output_tokens": round(proj_output),
        "by_model": model_forecasts,
        "alternatives": alternatives,
        "subscription_efficiency": _compute_efficiency(proj_by_model, catalog_dict, aliases),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_forecast(report: dict, horizon: int) -> None:
    if "error" in report:
        print(f"Error: {report['error']}")
        return

    hp = report["historical_period"]
    print(f"\n=== {horizon}-Day Forecast ===")
    print(f"  Historical period  : {hp['start']} to {hp['end']} ({hp['days_with_data']} days with data)")
    print(f"  Projected cost     : ${report['projected_total_cost_usd']:.4f} USD")
    print(f"  Projected calls    : {report['projected_calls']:,}")
    print(f"  Projected tokens   : {report['projected_input_tokens'] + report['projected_output_tokens']:,}")

    print("\nBy model (projected cost):")
    for m in report["by_model"][:8]:
        intel = f"  IQ:{m['intelligence_index']:.1f}" if m.get("intelligence_index") else ""
        print(
            f"  {m['model_id']:<45} "
            f"${m['projected_cost_usd']:.4f}  "
            f"({m['usage_share_pct']:.1f}%)"
            f"{intel}"
        )

    if report["alternatives"]:
        print("\nCost-saving alternatives:")
        for alt in report["alternatives"]:
            print(f"  Replace {alt['for_model']} (projected ${alt['projected_cost_usd']:.4f}):")
            for opt in alt["cheaper_options"]:
                intel = f"  IQ:{opt['intelligence_index']:.1f}" if opt.get("intelligence_index") else ""
                print(
                    f"    -> {opt['model_id']:<40} "
                    f"saves {opt['savings_pct']:.0f}%  "
                    f"(${opt['potential_savings_usd']:.4f})"
                    f"{intel}"
                )

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
    parser = argparse.ArgumentParser(description="Forecast LLM usage costs")
    parser.add_argument("usage", help="Usage log file (.json or .csv)")
    parser.add_argument("--catalog", "-c", required=True, help="Model catalog JSON (from fetch_models.py)")
    parser.add_argument("--days", "-d", type=int, default=30, help="Forecast horizon in days (default: 30)")
    parser.add_argument("--output", "-o", default=None, help="Save JSON report to this path")
    args = parser.parse_args()

    report = forecast(args.usage, args.catalog, args.days)

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Forecast saved to: {args.output}")

    _print_forecast(report, args.days)


if __name__ == "__main__":
    main()
