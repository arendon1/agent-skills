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
import subprocess
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


def _monthly_efficiency(usage: list[dict], catalog: dict[str, dict], aliases: dict[str, str], subs: dict) -> dict:
    if not subs:
        return {"monthly": [], "summary": {}}

    providers = subs.get("providers", {})

    monthly_provider_stats: dict[str, dict] = defaultdict(
        lambda: defaultdict(lambda: {"input": 0, "output": 0, "or_cost": 0.0})
    )

    for entry in usage:
        model_id = entry.get("model_id", "")
        provider = _provider_for_model(model_id)
        if not provider or provider not in providers:
            continue
        if providers[provider].get("type") == "api_only":
            continue

        ts = entry.get("timestamp", "")
        if not ts:
            continue
        month = ts[:7]

        inp = int(entry.get("input_tokens", 0) or 0)
        out = int(entry.get("output_tokens", 0) or 0)

        resolved = aliases.get(model_id, model_id)
        model = catalog.get(resolved)
        cost = 0.0
        if model:
            pricing = model.get("pricing", {})
            prompt_price = float(pricing.get("prompt", 0) or 0)
            completion_price = float(pricing.get("completion", 0) or 0)
            cost = inp * prompt_price + out * completion_price

        monthly_provider_stats[month][provider]["input"] += inp
        monthly_provider_stats[month][provider]["output"] += out
        monthly_provider_stats[month][provider]["or_cost"] += cost

    monthly_records = []

    for month in sorted(monthly_provider_stats.keys()):
        for prov_id, prov_info in providers.items():
            stats = monthly_provider_stats[month].get(prov_id)
            if not stats:
                continue
            if prov_info.get("type") == "api_only":
                continue

            or_cost = stats["or_cost"]
            inp = stats["input"]
            out = stats["output"]

            tiers = prov_info.get("tiers", [])
            for tier in tiers:
                monthly_price = tier.get("price_monthly_usd", 0)
                if monthly_price <= 0:
                    continue

                if prov_id == "opencode-go":
                    cap = prov_info.get("limits", {}).get("per_month_usd", 60)
                    if or_cost <= cap:
                        sub_value = or_cost
                        overage = 0.0
                    else:
                        sub_value = cap
                        overage = or_cost - cap
                    cap_used_pct = round((or_cost / cap) * 100, 1) if cap > 0 else 0.0
                    subscription_cost_usd = monthly_price

                elif prov_id == "github-copilot":
                    credit_usd_rate = prov_info.get("credit_usd_rate", 0.01)
                    credits_used = or_cost / credit_usd_rate if credit_usd_rate > 0 else 0
                    credit_allowance = tier.get("credits_monthly", 0)
                    sub_value = min(or_cost, credit_allowance * credit_usd_rate)
                    cap = credit_allowance * credit_usd_rate
                    cap_used_pct = round((or_cost / cap) * 100, 1) if cap > 0 else 0.0
                    overage = max(0.0, or_cost - cap)
                    subscription_cost_usd = monthly_price

                else:
                    cap = monthly_price
                    sub_value = min(or_cost, cap)
                    overage = max(0.0, or_cost - cap)
                    cap_used_pct = round((or_cost / cap) * 100, 1) if cap > 0 else 0.0
                    subscription_cost_usd = monthly_price

                efficiency_ratio = round(sub_value / subscription_cost_usd, 2) if subscription_cost_usd > 0 else 0.0

                monthly_records.append({
                    "provider": prov_id,
                    "tier": tier["name"],
                    "month": month,
                    "tokens_input": inp,
                    "tokens_output": out,
                    "openrouter_cost_usd": round(or_cost, 4),
                    "subscription_value_usd": round(sub_value, 4),
                    "cap_used_pct": cap_used_pct,
                    "overage_paid_usd": round(overage, 4),
                    "subscription_cost_usd": round(subscription_cost_usd, 4),
                    "efficiency_ratio": efficiency_ratio,
                })

    if not monthly_records:
        return {"monthly": [], "summary": {}}

    seen_month_prov = {}
    for r in monthly_records:
        key = (r["month"], r["provider"])
        if key not in seen_month_prov or r["subscription_cost_usd"] < seen_month_prov[key]["subscription_cost_usd"]:
            seen_month_prov[key] = r

    total_subscription_paid = sum(r["subscription_cost_usd"] for r in seen_month_prov.values())
    total_subscription_value = sum(r["subscription_value_usd"] for r in seen_month_prov.values())

    all_months = set(r["month"] for r in monthly_records)
    total_months = len(all_months)

    capped_pairs = set()
    total_overage_sum = 0.0
    for r in monthly_records:
        if r["cap_used_pct"] >= 100:
            capped_pairs.add((r["month"], r["provider"]))
        total_overage_sum += r["overage_paid_usd"]

    months_capped = len(capped_pairs)

    overall_efficiency = round(total_subscription_value / total_subscription_paid, 2) if total_subscription_paid > 0 else 0.0

    return {
        "monthly": monthly_records,
        "summary": {
            "total_months": total_months,
            "total_subscription_paid": round(total_subscription_paid, 4),
            "total_subscription_value": round(total_subscription_value, 4),
            "overall_efficiency": overall_efficiency,
            "months_capped": months_capped,
            "total_overage": round(total_overage_sum, 4),
        },
    }


def _detect_model_jumps(session_ids: list[str]) -> dict[str, bool]:
    if not session_ids:
        return {}
    ids_str = ", ".join(f"'{sid}'" for sid in session_ids)
    try:
        result = subprocess.run(
            ["opencode", "db",
             f"SELECT DISTINCT session_id FROM session_message WHERE type = 'model-switched' AND session_id IN ({ids_str})",
             "--format", "json"],
            capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, OSError):
        return {}
    if result.returncode != 0:
        return {}
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    return {r["session_id"]: True for r in rows if isinstance(r, dict)}


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
    by_model: dict[str, dict] = defaultdict(lambda: {
        "calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_cost": 0.0,
        "sessions": 0,
        "sessions_with_model_jumps": 0,
    })
    unknown_models: set[str] = set()

    aliases = load_aliases()
    model_sessions: dict[str, set[str]] = defaultdict(set)
    session_ids: set[str] = set()

    for entry in usage:
        model_id: str = entry.get("model_id", "unknown")
        resolved_id = aliases.get(model_id, model_id)
        model = catalog.get(resolved_id)
        inp = int(entry.get("input_tokens", 0) or 0)
        out = int(entry.get("output_tokens", 0) or 0)
        sid = entry.get("session_id", "")

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

        if sid:
            provider = _provider_for_model(model_id)
            if provider in ("opencode-go", "github-copilot"):
                session_ids.add(sid)
                model_sessions[model_id].add(sid)

    model_jumps = _detect_model_jumps(list(session_ids))

    for model_id, sessions in model_sessions.items():
        by_model[model_id]["sessions"] = len(sessions)
        by_model[model_id]["sessions_with_model_jumps"] = sum(1 for s in sessions if s in model_jumps)

    total_cost = sum(v["total_cost"] for v in by_model.values())
    total_calls = sum(v["calls"] for v in by_model.values())
    total_input = sum(v["input_tokens"] for v in by_model.values())
    total_output = sum(v["output_tokens"] for v in by_model.values())

    total_sessions = len(session_ids)
    jumped_sessions = len(model_jumps)
    pct_jumped = round(jumped_sessions / total_sessions * 100, 1) if total_sessions else 0.0

    subs = load_subscriptions()
    subscription_efficiency = _monthly_efficiency(usage, catalog, aliases, subs) if subs else {"monthly": [], "summary": {}}

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
        "subscription_efficiency": subscription_efficiency,
        "model_jumps": {
            "total_sessions": total_sessions,
            "jumped_sessions": jumped_sessions,
            "pct": pct_jumped,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_report(report: dict) -> None:
    from chart_utils import hbar, gauge, sparkline

    s = report["summary"]
    print("\n=== Cost Analysis Summary ===")
    print(f"  Total cost     : ${s['total_cost_usd']:.4f} USD")
    print(f"  Total calls    : {s['total_calls']:,}")
    print(f"  Total tokens   : {s['total_input_tokens'] + s['total_output_tokens']:,}")
    print(f"  Avg cost/call  : ${s['avg_cost_per_call_usd']:.6f} USD")
    print(f"  Avg in/out     : {s['avg_input_tokens_per_call']:.0f} / {s['avg_output_tokens_per_call']:.0f} tokens")

    print("\nTop models by spend:")
    top = report["by_model"][:8]
    if top:
        max_cost = max(m["total_cost_usd"] for m in top)
        for m in top:
            suffix = f"${m['total_cost_usd']:.2f}  ({m['cost_share_pct']:.1f}%)"
            print(hbar(m["model_id"], m["total_cost_usd"], max_cost, suffix))

    if report["unknown_models"]:
        print(f"\nWarning: {len(report['unknown_models'])} model(s) not found in catalog (no pricing):")
        for mid in report["unknown_models"]:
            print(f"  - {mid}")
        print("  Tip: re-run fetch_models.py to refresh the catalog.")

    eff = report.get("subscription_efficiency", {})
    monthly = eff.get("monthly", [])
    if monthly:
        print("\n=== Monthly Efficiency ===")
        by_provider = {}
        for m in monthly:
            by_provider.setdefault(m["provider"], []).append(m)
        for prov_id, entries in by_provider.items():
            caps = [e["cap_used_pct"] for e in entries]
            months = " ".join(e["month"][2:] for e in entries[-12:])
            print(f"\n  {prov_id}:")
            print("  " + sparkline(caps, months[-12:]))
            last = entries[-1]
            print("  " + gauge(prov_id.split("-")[0][:6], last["efficiency_ratio"]))
        summary = eff.get("summary", {})
        if summary:
            print(f"\n  {summary['total_months']} months, ${summary['total_subscription_paid']:.2f} paid, ${summary['total_subscription_value']:.2f} value")
            if summary.get("total_overage", 0) > 0:
                print(f"  Overages: ${summary['total_overage']:.2f}")
            if summary.get("months_capped", 0) > 0:
                print(f"  {summary['months_capped']} month(s) hit the cap")

    mj = report.get("model_jumps", {})
    if mj and mj.get("total_sessions", 0) > 0:
        print(f"\nModel jumping detected in {mj['jumped_sessions']} of {mj['total_sessions']} sessions ({mj['pct']}%).")
        print("Subagent model usage is untracked at the DB level.")


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
