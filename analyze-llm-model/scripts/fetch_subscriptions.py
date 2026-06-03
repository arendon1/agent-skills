"""
Subscription cache-gate orchestrator.

Checks if references/subscriptions.json is fresh (within cache_ttl_days).
If fresh: prints cached data to stdout, exits 0.
If stale: prints a RESEARCH_PROMPT to stdout, exits 1.

The RESEARCH_PROMPT tells the agent to dispatch subagents per provider,
fetch current pricing pages, and write updated subscriptions.json.

Usage:
    python scripts/fetch_subscriptions.py                    # check/research
    python scripts/fetch_subscriptions.py --ttl 0            # force research
    python scripts/fetch_subscriptions.py --providers opencode-go  # single provider
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
SUBSCRIPTIONS_PATH = REFERENCES_DIR / "subscriptions.json"


def _is_fresh(file_path: Path, ttl_days: int) -> bool:
    if not file_path.exists():
        return False
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        updated = data.get("last_updated", "")
        if not updated:
            return False
        last = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - last
        cache_ttl = data.get("cache_ttl_days", ttl_days)
        return age < timedelta(days=cache_ttl)
    except (json.JSONDecodeError, ValueError, KeyError):
        return False


def _print_cached() -> None:
    data = json.loads(SUBSCRIPTIONS_PATH.read_text(encoding="utf-8"))
    print(json.dumps(data, indent=2))
    sys.exit(0)


def _print_research_prompt(providers: list[str] | None = None) -> None:
    data = {}
    if SUBSCRIPTIONS_PATH.exists():
        try:
            data = json.loads(SUBSCRIPTIONS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            pass

    all_providers = data.get("providers", {})

    if providers:
        all_providers = {k: v for k, v in all_providers.items() if k in providers}

    print("RESEARCH_PROMPT")
    print("===============")
    print()
    print("The subscription pricing cache is stale or missing.")
    print("Dispatch subagents to research current pricing for each provider below.")
    print("Each subagent must return a valid JSON object matching the provider schema.")
    print("Merge all results and write to:", SUBSCRIPTIONS_PATH)
    print()
    print("Update last_updated to the current ISO 8601 timestamp.")
    print()

    for provider_id, info in sorted(all_providers.items()):
        prov_type = info.get("type", "api_only")
        print(f"--- Provider: {info.get('name', provider_id)} ({provider_id}) ---")
        print(f"    Type: {prov_type}")
        print(f"    Research URL: (use web search to find current pricing page)")
        if prov_type == "token_budget":
            print(f"    Schema: {{'tiers': [{{'name': str, 'price_monthly_usd': float, ...}}]}}")
            if info.get("model_pricing_per_1m"):
                print(f"    Also capture: model_pricing_per_1m with {{input, output, cached_read}} per 1M tokens")
            if info.get("credit_usd_rate"):
                print(f"    Credit rate: {info['credit_usd_rate']} USD per credit")
        elif prov_type == "rate_access":
            print(f"    Schema: {{'tiers': [{{'name': str, 'price_monthly_usd': float, 'usage_multiplier': int}}]}}")
        else:
            print(f"    Schema: {{'type': 'api_only'}} (no subscription)")
        print()

    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check subscription cache freshness or trigger research"
    )
    parser.add_argument("--ttl", type=int, default=None,
                        help="Override cache TTL in days (0 = force research)")
    parser.add_argument("--providers", type=str, default=None,
                        help="Comma-separated provider IDs to research (default: all)")
    args = parser.parse_args()

    ttl_days = args.ttl if args.ttl is not None else 30

    if args.ttl == 0:
        _print_research_prompt(
            args.providers.split(",") if args.providers else None
        )
    elif _is_fresh(SUBSCRIPTIONS_PATH, ttl_days):
        _print_cached()
    else:
        _print_research_prompt(
            args.providers.split(",") if args.providers else None
        )


if __name__ == "__main__":
    main()
