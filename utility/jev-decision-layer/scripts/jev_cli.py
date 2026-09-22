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

import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

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


# --------------------------------------------------------------------------- #
# Backend policy — "usá Laya cuando corresponda", sin tener que acordarse
# --------------------------------------------------------------------------- #
def probe_backend(name: str) -> bool:
    """¿Este backend está DISPONIBLE ahora? Clave presente o servidor respondiendo."""
    if name == "fallback":
        return True
    if name == "laya":
        base = os.environ.get("JEV_BASE_URL")
        if base and base.startswith(("http://127.0.0.1", "http://localhost")):
            return _laya_health(base)
        # Sin env, probamos el puerto configurado — puede estar corriendo igual.
        try:
            from jev_client import _load_config  # noqa: PLC0415
            cfg = _load_config() or {}
            port = int((cfg.get("laya") or {}).get("port_base", 8791))
        except Exception:  # noqa: BLE001
            port = 8791
        return _laya_health(f"http://127.0.0.1:{port}")
    if name == "openrouter":
        return bool(os.environ.get("OPENROUTER_API_KEY"))
    if name == "vercel":
        return bool(os.environ.get("VERCEL_API_KEY") or os.environ.get("AI_GATEWAY_API_KEY"))
    if name in ("typesafe", "live"):
        return bool(os.environ.get("TYPESAFE_API_KEY"))
    return False


def _laya_health(base: str, timeout: float = 1.2) -> bool:
    try:
        import urllib.request  # noqa: PLC0415
        with urllib.request.urlopen(base.rstrip("/") + "/health", timeout=timeout) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception:  # noqa: BLE001 — un backend caído no es un error, es un fallback
        return False


def resolve_backend(preset: str | None = None) -> tuple[str, list[dict]]:
    """Aplica la política del preset: primer backend PREFERIDO que esté DISPONIBLE.

    Devuelve (backend_elegido, rastro_de_pruebas). El rastro importa: deja ver
    que Laya se prefirió y no estaba, en vez de caer a OpenRouter en silencio.
    """
    from jev_client import _load_config  # noqa: PLC0415
    cfg = _load_config() or {}
    policy = cfg.get("backend_policy") or {}
    chain = (policy.get(preset or "") or policy.get("default")
             or ["laya", "openrouter", "fallback"])
    trace = []
    for name in chain:
        ok = probe_backend(name)
        trace.append({"backend": name, "available": ok})
        if ok:
            return name, trace
    return "fallback", trace


def ensure_backend(preset: str | None, auto_laya: bool) -> tuple[str, list[dict], str | None]:
    """Como resolve_backend, pero con --auto-laya arranca Laya si la política la
    prefiere y no responde. Devuelve (backend, traza, aviso).

    Arrancar Laya levanta un proceso de ~3.7 GB, así que NUNCA es implícito:
    requiere JEV_AUTO_LAYA=1 o --auto-laya.
    """
    chosen, trace = resolve_backend(preset)
    from jev_client import _load_config  # noqa: PLC0415
    cfg = _load_config() or {}
    chain = (cfg.get("backend_policy") or {}).get(preset or "") or \
            (cfg.get("backend_policy") or {}).get("default") or []

    if chosen != "laya" and auto_laya and "laya" in chain:
        laya_cfg = cfg.get("laya") or {}
        py = os.path.expanduser(laya_cfg.get("python", ""))
        if py and Path(py).is_file():
            runner = Path(__file__).resolve().parent / "laya_on_demand.py"
            cmd = [sys.executable, str(runner), "--python", py,
                   "--port-base", str(laya_cfg.get("port_base", 8791)), "up"]
            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=240, check=False)
                if probe_backend("laya"):
                    return "laya", trace + [{"backend": "laya", "available": True,
                                             "started": True}], "laya_arrancada"
                return chosen, trace, "auto_laya_no_respondio"
            except Exception as e:  # noqa: BLE001
                return chosen, trace, f"auto_laya_fallo:{type(e).__name__}"
        return chosen, trace, "auto_laya_sin_interprete"

    warn = None
    if chosen != "laya" and trace and trace[0].get("backend") == "laya" \
            and not trace[0].get("available"):
        warn = "laya_preferida_pero_no_corria — se usó " + chosen
    return chosen, trace, warn


def build_questions(args: argparse.Namespace) -> dict:
    """Construye el dict de preguntas desde --preset + --question.

    Pasa el dict COMPLETO del preset (type, instructions, options, range_max),
    NO solo (type, instructions): los presets con `choice` o `score` necesitan sus
    opciones, y perderlas los rompe con "options required" / "range_max required".
    Bug real: 4 de los 6 presets fallaban por esto.
    """
    questions: dict = {}
    if args.preset:
        preset = PRESETS.get(args.preset)
        if preset is None:
            raise KeyError(args.preset)
        for k, v in preset.items():
            questions[k] = dict(v)
    for q in args.question or []:
        if "=" not in q or ":" not in q:
            continue
        k, payload_q = q.split("=", 1)
        t, instr = payload_q.split(":", 1)
        questions[k.strip()] = (t.strip().strip('"').strip("'"),
                                instr.strip().strip('"').strip("'"))
    return questions


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
        try:
            questions = build_questions(args)
        except KeyError as e:
            print(json.dumps({"error": f"unknown preset: {e.args[0]}"}))
            return 3

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
        try:
            questions = build_questions(args)
        except KeyError as e:
            print(json.dumps({"error": f"unknown preset: {e.args[0]}"}))
            return 3

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

    # SIN --backend explícito, manda la POLÍTICA del preset (backend_policy en
    # jev.json): primer backend preferido que esté disponible. La traza va en la
    # salida para que "Laya se prefirió y no corría" se vea, no se adivine.
    backend_trace: list[dict] = []
    backend_warning = None
    if not backend:
        auto = args.auto_laya or bool(int(os.environ.get("JEV_AUTO_LAYA", "0")))
        backend, backend_trace, backend_warning = ensure_backend(args.preset, auto)

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
        "backend_trace": backend_trace or None,
        "backend_warning": backend_warning,
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
    pd.add_argument("--auto-laya", action="store_true",
                    help="Si la política prefiere Laya y no responde, arrancarla "
                         "(levanta un proceso de ~3.7 GB; nunca es implícito).")
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
