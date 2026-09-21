#!/usr/bin/env python3
"""
JEV CLI — subprocess entry point for cross-skill consumption (§12).

Other skills in this repo MUST NOT import jev_client directly. They invoke this
CLI as a subprocess. Input via flags or stdin-JSON. Output is always JSON.

Usage:
    python jev_cli.py classify --state "..." --preset slide_done_v1
    python jev_cli.py classify --state "..." \
        --question score_at_max="noul:Did this score max?"
    python jev_cli.py list-presets
    echo '{"state": "...", "questions": {...}}' | python jev_cli.py classify --stdin
    python jev_cli.py cost-report [--since YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jev_client import JEV, COST_LOG  # noqa: E402
from jev_schemas import PRESETS, list_presets, decide as apply_decision  # noqa: E402


def _load_thresholds() -> dict:
    from jev_client import _load_config  # noqa: PLC0415 — local, evita ciclo en import
    return (_load_config() or {}).get("thresholds_by_backend", {})


def threshold_for(mode: str, preset: str | None = None) -> float | None:
    """Threshold for a backend. The threshold belongs to the BACKEND, not the preset."""
    return (_load_thresholds().get(mode) or {}).get("noul_default")


def cmd_classify(args: argparse.Namespace) -> int:
    if args.stdin:
        try:
            payload = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"invalid JSON on stdin: {e}"}), file=sys.stderr)
            return 2
        state = payload.get("state", "")
        questions = payload.get("questions", {})
        backend = payload.get("backend") or args.backend
    else:
        backend = args.backend
        state = args.state or ""
        questions = {}
        if args.preset:
            preset = PRESETS.get(args.preset)
            if not preset:
                print(json.dumps({"error": f"unknown preset: {args.preset}"}))
                return 3
            for k, v in preset.items():
                questions[k] = (v["type"], v["instructions"])
        for q in args.question or []:
            if "=" not in q or ":" not in q:
                continue
            k, payload_q = q.split("=", 1)
            t, instr = payload_q.split(":", 1)
            t = t.strip().strip('"').strip("'")
            instr = instr.strip().strip('"').strip("'")
            questions[k.strip()] = (t, instr)

    # Normalize JSON-deserialized lists to tuples (JSON has no tuples; we accepted
    # the sugar form which is a 2-3 element list/tuple).
    if isinstance(questions, dict):
        for k, v in list(questions.items()):
            if isinstance(v, list):
                questions[k] = tuple(v)

    if not state:
        print(json.dumps({"error": "state is required"}))
        return 4
    if not questions:
        print(json.dumps({"error": "at least one question required (use --preset or --question)"}))
        return 5

    client = JEV(backend=backend)
    verdict = client.classify(state, questions)
    print(json.dumps(verdict.as_dict(), indent=2 if args.pretty else None, ensure_ascii=False))
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    """Classify AND apply the preset's decision rule with a backend threshold."""
    if args.stdin:
        try:
            payload = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"invalid JSON on stdin: {e}"}), file=sys.stderr)
            return 2
        state = payload.get("state", "")
        questions = payload.get("questions", {})
        backend = payload.get("backend") or args.backend
    else:
        backend = args.backend
        state = args.state or ""
        questions = {}
        if args.preset:
            preset = PRESETS.get(args.preset)
            if not preset:
                print(json.dumps({"error": f"unknown preset: {args.preset}"}))
                return 3
            for k, v in preset.items():
                questions[k] = (v["type"], v["instructions"])
        for q in args.question or []:
            if "=" not in q or ":" not in q:
                continue
            k, payload_q = q.split("=", 1)
            t, instr = payload_q.split(":", 1)
            questions[k.strip()] = (t.strip().strip('"').strip("'"),
                                    instr.strip().strip('"').strip("'"))

    if isinstance(questions, dict):
        for k, v in list(questions.items()):
            if isinstance(v, list):
                questions[k] = tuple(v)

    if not state:
        print(json.dumps({"error": "state is required"}))
        return 4
    if not questions:
        print(json.dumps({"error": "at least one question required"}))
        return 5

    client = JEV(backend=backend)
    verdict = client.classify(state, questions)
    vd = verdict.as_dict()

    th = args.threshold if args.threshold is not None else threshold_for(verdict.mode, args.preset)
    decision = apply_decision(args.preset or "", vd["answers"], verdict.mode, th)

    out = {
        "decision": decision["decision"],
        "confident": decision["confident"],
        "mode": verdict.mode,
        "threshold": decision["threshold"],
        "reasons": decision["reasons"],
        "answers": vd["answers"],
        "cost_usd": verdict.cost_usd,
        "latency_ms": verdict.latency_ms,
        "preset": args.preset,
    }
    print(json.dumps(out, indent=2 if args.pretty else None, ensure_ascii=False))
    # Exit code: 0 = pass, 1 = fail, 3 = uncertain (so shell callers can branch)
    return {"pass": 0, "fail": 1}.get(decision["decision"], 3)


def cmd_laya(args: argparse.Namespace) -> int:
    """Delegate to laya_on_demand.py (up|down|status)."""
    import subprocess  # noqa: PLC0415
    here = Path(__file__).resolve().parent
    runner = here / "laya_on_demand.py"
    if not runner.is_file():
        print(json.dumps({"error": "laya_on_demand.py not found"}))
        return 3
    cmd = [sys.executable, str(runner), getattr(args, "laya_action", "status")]
    if args.python_for_laya:
        cmd += ["--python", args.python_for_laya]
    if args.port_base:
        cmd += ["--port-base", str(args.port_base)]
    # El runner imprime el JSON util en stdout y el progreso en stderr.
    return subprocess.call(cmd)


def cmd_list_presets(args: argparse.Namespace) -> int:
    print(json.dumps({"presets": list_presets()}, indent=2))
    return 0


def cmd_cost_report(args: argparse.Namespace) -> int:
    if not COST_LOG.is_file():
        print(json.dumps({"calls": 0, "by_mode": {}, "by_day": {}, "total_usd": 0}))
        return 0

    since = dt.date.fromisoformat(args.since) if args.since else None
    by_mode: dict[str, int] = {}
    by_day: dict[str, int] = {}
    total = 0.0
    calls = 0
    for line in COST_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = rec.get("ts", "")
        if since and ts[:10] < since.isoformat():
            continue
        mode = rec.get("mode", "?")
        by_mode[mode] = by_mode.get(mode, 0) + 1
        day = ts[:10]
        by_day[day] = by_day.get(day, 0) + 1
        total += float(rec.get("cost_usd", 0))
        calls += 1

    print(json.dumps(
        {"calls": calls, "by_mode": by_mode, "by_day": by_day, "total_usd": round(total, 6)},
        indent=2,
    ))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="JEV Decision Layer CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("classify", help="Run a decision call.")
    pc.add_argument("--state", help="Text/JSON state to evaluate. Required unless --stdin.")
    pc.add_argument("--preset", help="Use a named schema preset (e.g. slide_done_v1).")
    pc.add_argument("--backend", choices=["openrouter", "vercel", "typesafe", "laya", "fallback"],
                    help="Force a specific backend.")
    pc.add_argument("--question", action="append", default=[],
                    help='Inline: key="type:instructions". Repeatable.')
    pc.add_argument("--stdin", action="store_true", help="Read payload as JSON from stdin.")
    pc.add_argument("--pretty", action="store_true")
    pc.set_defaults(func=cmd_classify)

    pl = sub.add_parser("list-presets", help="List available preset schemas.")
    pl.set_defaults(func=cmd_list_presets)

    cr = sub.add_parser("cost-report", help="Aggregate spend from cost-log.jsonl.")
    cr.add_argument("--since", help="Filter to entries on/after YYYY-MM-DD.")
    cr.set_defaults(func=cmd_cost_report)

    pd = sub.add_parser("decide",
                        help="Classify AND apply the preset's decision rule (exit 0=pass, 1=fail, 3=uncertain).")
    pd.add_argument("--state", help="Text/JSON state. Required unless --stdin.")
    pd.add_argument("--preset", help="Preset to evaluate (e.g. slide_done_v1).")
    pd.add_argument("--backend", choices=["openrouter", "vercel", "typesafe", "laya", "fallback"])
    pd.add_argument("--question", action="append", default=[],
                    help='Inline: key="type:instructions". Repeatable.')
    pd.add_argument("--stdin", action="store_true")
    pd.add_argument("--threshold", type=float, default=None,
                    help="Override the backend's configured threshold.")
    pd.add_argument("--pretty", action="store_true")
    pd.set_defaults(func=cmd_decide)

    pl = sub.add_parser("laya", help="Manage an on-demand Laya server (up|down|status).")
    pl.add_argument("laya_action", nargs="?", default="status",
                    choices=["up", "down", "status"])
    pl.add_argument("--python-for-laya", help="Interpreter that has laya installed.")
    pl.add_argument("--port-base", type=int, default=8791)
    pl.set_defaults(func=cmd_laya)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
