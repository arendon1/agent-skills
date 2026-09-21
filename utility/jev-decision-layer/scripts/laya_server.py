#!/usr/bin/env python3
"""
laya_server.py — wrapper HTTP mínimo sobre la librería Laya.

Laya (`pip install laya`) es una librería pura: no trae servidor. Este wrapper
expone el shape JEV (`state` + `questions` tipadas) sobre HTTP en 127.0.0.1, para
que `jev_client._http_call_laya` lo consuma sin cambios.

Diseño on-demand: se arranca, atiende el run, se mata. Sin daemon, sin
persistencia, sin sudo. Bind SOLO a 127.0.0.1 (directiva Tier 3 §11).

Traducción de shape JEV -> Laya:
  noul   -> noul                                (idéntico)
  choice -> choice con `criteria` {opt: opt}    (Laya usa dict, no lista)
  score  -> score con `criteria` [nivel, ...]   (Laya usa lista, 0-indexado)

Traducción de vuelta:
  noul   -> {type:"noul", noul: p}
  choice -> {type:"choice", choice: opción, probabilities: {opción: conf}}
  score  -> {type:"score", score: round(laya_score)+1, confidence: conf}   (1..N)

Uso:
    python laya_server.py --port 8791 [--device mps] [--model convaiinnovations/laya]

Endpoints:
    GET  /health          -> {"ok": true, "model": "...", "load_s": 23.4}
    POST /v1/systemone    -> {"answers": {...}, "usage": {...}}
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

_AGENT = None
_LOAD_S = 0.0
_MODEL_ID = "convaiinnovations/laya"
_LOCK = threading.Lock()


# --------------------------------------------------------------------------- #
# Traducción JEV -> Laya
# --------------------------------------------------------------------------- #
def to_laya_questions(jev_questions: dict) -> dict:
    out = {}
    for k, q in (jev_questions or {}).items():
        t = q.get("type")
        entry: dict[str, Any] = {
            "type": t,
            "instructions": q.get("instructions", ""),
        }
        if t == "choice":
            opts = q.get("options") or []
            # Laya quiere {opción: descripción}; sin descripción, la opción es su propia descripción.
            entry["criteria"] = {o: o for o in opts}
        elif t == "score":
            rng = q.get("range") or [1, q.get("range_max") or 5]
            n = int(rng[1]) - int(rng[0]) + 1
            entry["criteria"] = [f"level {i}" for i in range(n)]
        out[k] = entry
    return out


# --------------------------------------------------------------------------- #
# Traducción Laya -> JEV
# --------------------------------------------------------------------------- #
def to_jev_answers(laya_result: dict, jev_questions: dict) -> dict:
    raw = (laya_result or {}).get("answers") or {}
    out: dict[str, Any] = {}
    for k, q in (jev_questions or {}).items():
        a = raw.get(k) or {}
        t = q.get("type")
        if t == "noul":
            p = float(a.get("noul", a.get("confidence", 0.0)) or 0.0)
            out[k] = {"type": "noul", "noul": p, "probabilities": None}
        elif t == "choice":
            pick = a.get("choice")
            conf = a.get("confidence")
            probs = a.get("probabilities") or ({pick: conf} if pick is not None and conf is not None else {})
            out[k] = {"type": "choice", "choice": pick, "probabilities": probs,
                      "confidence": conf}
        elif t == "score":
            # Laya: 0-indexado float. JEV: 1..N entero.
            s = a.get("score")
            try:
                s_int = int(round(float(s))) + 1
            except (TypeError, ValueError):
                s_int = 1
            out[k] = {"type": "score", "score": s_int,
                      "confidence": a.get("confidence"), "raw_score": s}
        else:
            out[k] = a
    return out


# --------------------------------------------------------------------------- #
# HTTP handler
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_a):  # silencio: el stdout es para las mediciones
        pass

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/health":
            self._send(200, {"ok": _AGENT is not None, "model": _MODEL_ID,
                             "load_s": round(_LOAD_S, 2)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/systemone":
            self._send(404, {"error": "not found"})
            return
        if _AGENT is None:
            self._send(503, {"error": "model not loaded"})
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            req = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError) as e:
            self._send(400, {"error": f"bad json: {e}"})
            return

        state = req.get("state", "")
        jev_questions = req.get("questions") or {}
        if not jev_questions:
            self._send(400, {"error": "questions required"})
            return

        try:
            laya_q = to_laya_questions(jev_questions)
            with _LOCK:                       # Laya no es necesariamente thread-safe
                t0 = time.time()
                result = _AGENT.predict(state, laya_q)
                elapsed_ms = int((time.time() - t0) * 1000)
        except Exception as e:  # noqa: BLE001 — el server nunca debe morir por una request
            self._send(500, {"error": f"{type(e).__name__}: {str(e)[:300]}"})
            return

        self._send(200, {
            "answers": to_jev_answers(result, jev_questions),
            "usage": {"input_tokens": (result or {}).get("usage", {}).get("input_tokens", 0),
                      "output_tokens": 0},
            "elapsed_ms": elapsed_ms,
        })


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Servidor HTTP mínimo para Laya.")
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--model", default="convaiinnovations/laya")
    ap.add_argument("--device", default=None, help="mps | cpu | cuda (default: autodetecta)")
    args = ap.parse_args()

    global _AGENT, _LOAD_S, _MODEL_ID
    _MODEL_ID = args.model

    print(json.dumps({"event": "loading", "model": args.model, "device": args.device}),
          flush=True)
    t0 = time.time()
    import laya
    agent = laya.load(args.model, device=args.device)
    _AGENT = agent
    _LOAD_S = time.time() - t0
    print(json.dumps({"event": "ready", "load_s": round(_LOAD_S, 2),
                      "port": args.port}), flush=True)

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())