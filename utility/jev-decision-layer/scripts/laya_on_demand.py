#!/usr/bin/env python3
"""
laya_on_demand.py — arranca Laya, ejecuta un comando, y la mata.

Patrón on-demand (directiva Tier 3 §11): sin daemon, sin persistencia, sin sudo.
Sostenido en reposo = 0 bytes. Durante un run = ~3.7 GB por la duración.

    # Ejecuta un comando con Laya caliente; la mata al terminar.
    python laya_on_demand.py run -- python h5p_solve.py --course-id 16564 --use-jev-guard

    # Solo arranca y deja el env listo para evaluar (imprime JEV_BASE_URL).
    python laya_on_demand.py up
    python laya_on_demand.py status
    python laya_on_demand.py down

Reutiliza un servidor ya vivo si lo encuentra (no arranca un segundo).
El puerto se elige libre desde --port-base.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE / "laya_server.py"
DEFAULT_PORT_BASE = 8791
READY_TIMEOUT_S = 180.0        # la carga medida fue 23s; 180s da margen para la 1a descarga


# --------------------------------------------------------------------------- #
# Probe
# --------------------------------------------------------------------------- #
def health(port: int, timeout: float = 1.5) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None


def find_live(port_base: int, span: int = 10) -> tuple[int, dict] | None:
    for p in range(port_base, port_base + span):
        h = health(p)
        if h and h.get("ok"):
            return p, h
    return None


def free_port(port_base: int, span: int = 10) -> int:
    import socket
    for p in range(port_base, port_base + span):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    raise RuntimeError(f"no hay puerto libre en {port_base}..{port_base+span}")


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #
def start(port: int, model: str, device: str | None, python: str | None = None) -> subprocess.Popen:
    py = python or sys.executable
    cmd = [py, str(SERVER), "--port", str(port), "--model", model]
    if device:
        cmd += ["--device", device]
    log = HERE.parent / "references" / "laya-server.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    f = log.open("a", encoding="utf-8")
    f.write(f"\n--- start {time.strftime('%Y-%m-%dT%H:%M:%S')} port={port} ---\n")
    f.flush()
    return subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)


def wait_ready(port: int, timeout: float = READY_TIMEOUT_S) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = health(port)
        if h and h.get("ok"):
            return h
        time.sleep(1.0)
    raise TimeoutError(f"Laya no respondió en {timeout:.0f}s (puerto {port})")


def stop(proc: subprocess.Popen | None, port: int) -> None:
    if proc is not None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=15)
        except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:  # noqa: BLE001
                pass
    # Barrido defensivo: cualquier servidor residual en ese puerto
    try:
        out = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True,
                             text=True, timeout=5).stdout.split()
        for pid in out:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except (ProcessLookupError, ValueError):
                pass
    except Exception:  # noqa: BLE001
        pass


def env_for(port: int) -> dict:
    return {"JEV_BACKEND": "laya", "JEV_BASE_URL": f"http://127.0.0.1:{port}"}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def ensure_up(args) -> tuple[int, dict, subprocess.Popen | None]:
    live = find_live(args.port_base)
    if live:
        port, h = live
        print(json.dumps({"event": "reused", "port": port, "model": h.get("model")}),
              file=sys.stderr)
        return port, h, None
    port = free_port(args.port_base)
    proc = start(port, args.model, args.device, python=args.python)
    print(json.dumps({"event": "starting", "port": port, "pid": proc.pid}),
          file=sys.stderr)
    h = wait_ready(port, timeout=args.timeout)
    print(json.dumps({"event": "ready", "port": port, "load_s": h.get("load_s")}),
          file=sys.stderr)
    return port, h, proc


def cmd_up(args) -> int:
    port, h, proc = ensure_up(args)
    print(json.dumps({"port": port, "pid": proc.pid if proc else None,
                      "env": env_for(port), "health": h}, indent=2))
    if proc is not None:
        print(f"\n(OJO: servidor arrancado con PID {proc.pid}. "
              f"Matar con: python {Path(__file__).name} down --port-base {args.port_base})",
              file=sys.stderr)
    return 0


def cmd_down(args) -> int:
    live = find_live(args.port_base)
    if not live:
        print(json.dumps({"event": "not_running"}))
        return 0
    port, _ = live
    stop(None, port)
    print(json.dumps({"event": "stopped", "port": port}))
    return 0


def cmd_status(args) -> int:
    live = find_live(args.port_base)
    if not live:
        print(json.dumps({"running": False}))
        return 1
    port, h = live
    print(json.dumps({"running": True, "port": port, "health": h}, indent=2))
    return 0


def cmd_run(args) -> int:
    if not args.cmd:
        print("ERROR: 'run' requiere un comando tras '--'", file=sys.stderr)
        return 2
    port, h, proc = ensure_up(args)
    env = {**os.environ, **env_for(port)}
    try:
        rc = subprocess.call(args.cmd, env=env)
    finally:
        if args.keep or proc is None:
            if proc is not None:
                print(json.dumps({"event": "left_running", "port": port, "pid": proc.pid}),
                      file=sys.stderr)
        else:
            stop(proc, port)
            print(json.dumps({"event": "stopped", "port": port}), file=sys.stderr)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="Laya on-demand: arranca, corre, mata.")
    ap.add_argument("--port-base", type=int, default=DEFAULT_PORT_BASE)
    ap.add_argument("--model", default="convaiinnovations/laya")
    ap.add_argument("--device", default=None, help="mps | cpu | cuda")
    ap.add_argument("--python", default=None, help="intérprete con laya instalado")
    ap.add_argument("--timeout", type=float, default=READY_TIMEOUT_S)
    sub = ap.add_subparsers(dest="action", required=True)

    for name, fn in (("up", cmd_up), ("down", cmd_down), ("status", cmd_status)):
        sp = sub.add_parser(name)
        sp.set_defaults(func=fn)

    sp = sub.add_parser("run")
    sp.add_argument("--keep", action="store_true",
                    help="no matar el servidor al terminar (por defecto SÍ se mata)")
    sp.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="comando a ejecutar (precedido por '--')")
    sp.set_defaults(func=cmd_run)

    args = ap.parse_args()
    # Limpia el '--' inicial que argparse deja en REMAINDER
    if getattr(args, "cmd", None) and args.cmd and args.cmd[0] == "--":
        args.cmd = args.cmd[1:]
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())