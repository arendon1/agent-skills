#!/usr/bin/env python3
"""
browser_nav_agent.py — Laya como capa de decisión para un agente de navegación CDP.

EL EXPERIMENTO
Un agente que navega un Chrome con CDP decide, en cada paso, QUÉ ESTADO tiene la
página delante y en consecuencia qué hacer. Hoy eso se resuelve con predicados JS
escritos a mano + polling (`wait_for(JS_TASK_READY_DOM, until=lambda r: r.get("ok"))`),
que es frágil: cada condición nueva es otra línea de heurística, y cada chequeo es
un round-trip al navegador.

Acá el estado se decide con UNA llamada a Laya sobre un resumen del DOM.

    while not done:
        dom  = snapshot()                      # 1 round-trip
        cls  = laya.classify(dom, page_state)  # 1 llamada, ~40ms, $0
        act  = ACTIONS[cls]                    # política explícita en código

POR QUÉ LAYA Y NO UN LLM
Medido: la clasificación de estado es una tarea de propiedad concreta — el fuerte
de un modelo tipo ModernBERT. Un LLM la hace en ~2s y con varianza; Laya en ~40ms.

Uso:
    # 1. Chrome efímero con CDP
    # 2. python browser_nav_agent.py --port 9225 --url http://127.0.0.1:8899/
    python browser_nav_agent.py --port 9225 --url http://127.0.0.1:8899/ --mode laya
    python browser_nav_agent.py --port 9225 --url http://127.0.0.1:8899/ --mode heuristica
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent / "scripts"))

import websocket  # noqa: E402

from jev_client import JEV  # noqa: E402

# --------------------------------------------------------------------------- #
# La política de navegación — explícita, en código legible
# --------------------------------------------------------------------------- #
PAGE_STATES = {
    "login_required": "A login form is visible: username and password inputs, "
                       "or a message saying the user is not identified.",
    "course_list": "A list of courses to choose from. Course name links are "
                    "visible; there is no activity list yet.",
    "course_page": "Inside one course. A list of activities is visible — links "
                    "to H5P content, forums or assignments, with a course heading.",
    "h5p_loading": "An interactive-content iframe exists but shows a spinner or "
                    "a placeholder, not the actual content yet.",
    "h5p_ready": "The interactive content has loaded: slides, a question, or a "
                  "presentation is rendered and ready to be worked on.",
    "error_page": "An error panel is visible stating the activity could not be "
                   "loaded, or a connection error.",
    "content_resolved": "The page shows a final grade at the maximum, such as "
                         "10,00 / 10,00 or 100%.",
}

QUESTION = {
    "page_state": ("choice",
                   "Which single state best describes this page right now?",
                   PAGE_STATES),
}

# Qué hace el agente por cada estado. La política vive en el código, NO en el modelo.
NEXT_ACTION = {
    "login_required": ("stop", "No se puede automatizar sin credenciales."),
    "course_list": ("click", ".course-item"),
    "course_page": ("click", ".activity.modtype_hvp"),
    "h5p_loading": ("wait", None),
    "h5p_ready": ("click", "a.activity"),
    "error_page": ("click", "a.activity"),
    "content_resolved": ("stop", "Actividad al máximo. Fin del flujo."),
}

# --------------------------------------------------------------------------- #
# Resumen del DOM — lo que se le pasa al clasificador
# --------------------------------------------------------------------------- #
SNAPSHOT_JS = r"""(() => {
  const vis = el => !!(el && el.getClientRects().length);
  const txt = (document.body.innerText || '').replace(/\s+/g, ' ').trim();
  const links = Array.from(document.querySelectorAll('a')).filter(vis)
      .map(a => (a.textContent || '').trim()).filter(Boolean).slice(0, 8);
  const forms = document.querySelectorAll('form').length;
  const inputs = Array.from(document.querySelectorAll('input')).filter(vis).length;
  const iframes = document.querySelectorAll('iframe').length;
  const spinner = document.querySelectorAll('.h5p-spinner, .loading, .spinner').length;
  const errbox = document.querySelectorAll('.errorbox, .alert-error, .errormessage').length;
  const h5p = document.querySelectorAll('.h5p-content, .h5p-iframe').length;
  const courses = document.querySelectorAll('.course-item').length;
  const acts = document.querySelectorAll('.activity').length;
  const success = /10,00|100,00|calificaci[oó]n/i.test(txt) ? 1 : 0;
  return JSON.stringify({
    title: document.title,
    text: txt.slice(0, 600),
    links, forms, inputs, iframes, spinner, errbox, h5p, courses, acts, success,
  });
})()"""


# --------------------------------------------------------------------------- #
# Cliente CDP mínimo
# --------------------------------------------------------------------------- #
class CDP:
    def __init__(self, port: int, timeout: float = 10.0):
        self.port = port
        self.timeout = timeout
        self._id = 0
        self.ws = None
        self.target = self._new_tab()

    def _new_tab(self) -> str:
        url = f"http://127.0.0.1:{self.port}/json/new?about:blank"
        req = urllib.request.Request(url, method="PUT")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())["webSocketDebuggerUrl"]

    def connect(self) -> None:
        self.ws = websocket.create_connection(self.target, timeout=self.timeout)

    def cmd(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                return msg.get("result", {})

    def goto(self, url: str) -> None:
        self.cmd("Page.navigate", {"url": url})
        time.sleep(0.9)

    def ev(self, js: str):
        r = self.cmd("Runtime.evaluate", {"expression": js, "returnByValue": True,
                                          "awaitPromise": True})
        return r.get("result", {}).get("value")

    def snapshot(self) -> dict:
        v = self.ev(SNAPSHOT_JS)
        try:
            return json.loads(v) if isinstance(v, str) else (v or {})
        except json.JSONDecodeError:
            return {"text": str(v)[:400]}

    def click(self, selector: str) -> bool:
        v = self.ev(f"""(() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return 'sin-elemento';
            el.click(); return 'ok';
        }})()""")
        time.sleep(1.1)
        return v == "ok"

    def close(self) -> None:
        try:
            if self.ws:
                self.ws.close()
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------------------- #
# Motor heurístico (lo que reemplazamos) — predicados + polling
# --------------------------------------------------------------------------- #
def classify_heuristic(s: dict) -> str:
    """Los predicados JS a mano que hoy viven dispersos en el solver."""
    t = (s.get("text") or "").lower()
    if "no se ha identificado" in t or s.get("forms", 0) > 0 and s.get("inputs", 0) > 0:
        return "login_required"
    if s.get("errbox", 0) > 0 or "error de conexión" in t:
        return "error_page"
    if s.get("success", 0) > 0:
        return "content_resolved"
    if s.get("spinner", 0) > 0:
        return "h5p_loading"
    if s.get("h5p", 0) > 0 and s.get("spinner", 0) == 0:
        return "h5p_ready"
    if s.get("courses", 0) > 0:
        return "course_list"
    if s.get("acts", 0) > 0:
        return "course_page"
    return "desconocido"


# --------------------------------------------------------------------------- #
def build_state_blob(s: dict) -> str:
    """Serializa el snapshot para el clasificador, con los cues que importan."""
    return (
        f"Page title: {s.get('title')}\n"
        f"Visible text: {s.get('text')}\n"
        f"Counts — forms={s.get('forms')} inputs={s.get('inputs')} "
        f"iframes={s.get('iframes')} spinners={s.get('spinner')} "
        f"error_panels={s.get('errbox')} h5p_elements={s.get('h5p')} "
        f"course_links={s.get('courses')} activity_links={s.get('acts')} "
        f"success_marker={s.get('success')}\n"
        f"Links: {s.get('links')}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Agente de navegación CDP con Laya como capa de decisión.")
    ap.add_argument("--port", type=int, required=True, help="puerto CDP del Chrome efímero")
    ap.add_argument("--url", required=True, help="URL inicial")
    ap.add_argument("--mode", choices=["laya", "heuristica"], default="laya")
    ap.add_argument("--backend", default="laya")
    ap.add_argument("--max-steps", type=int, default=12)
    ap.add_argument("--min-confidence", type=float, default=0.45,
                    help="Por debajo de esto, el agente NO actúa sobre la clasificación "
                         "(espera y reintenta) — evita falsos positivos terminales.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    b = CDP(args.port)
    b.connect()
    client = JEV(backend=args.backend) if args.mode == "laya" else None

    trace = []
    b.goto(args.url)
    t_start = time.time()

    for step in range(1, args.max_steps + 1):
        t0 = time.time()
        snap = b.snapshot()
        t_snap = (time.time() - t0) * 1000

        t0 = time.time()
        if args.mode == "laya":
            v = client.classify(build_state_blob(snap), QUESTION)
            state = v.answers["page_state"].value
            conf = v.answers["page_state"].probability or 0.0
            mode = v.mode
        else:
            state = classify_heuristic(snap)
            conf = None
            mode = "heuristica"
        t_cls = (time.time() - t0) * 1000

        action, arg = NEXT_ACTION.get(state, ("stop", f"estado desconocido: {state}"))

        # COMPUERTA DE CONFIANZA — SOLO para acciones TERMINALES.
        # Un `stop` es irreversible (el run termina), así que exige certeza: medido,
        # un DOM basura produjo `content_resolved` con conf 0.27 y habría cerrado
        # el flujo en falso. Un `click`, en cambio, ya se valida contra el DOM con
        # la guarda de precondición de abajo — gatearlo por confianza bloquea
        # clasificaciones CORRECTAS (medido: `h5p_ready` con 0.39 quedó en wait).
        low_conf = conf is not None and conf < args.min_confidence
        gated = low_conf and action == "stop"
        if gated:
            action, arg = "wait", f"conf {conf:.2f} < {args.min_confidence} — no cierro"

        # PRECONDICIÓN DE LA ACCIÓN. Si el modelo eligió un estado cuyo selector de
        # click no existe, la clasificación se contradice con el DOM. Se cae al
        # heurístico para ESE paso. Medido: Laya dijo `course_page` sobre la lista
        # de cursos (conf 0.56) y el click murió; sin esta guarda el run aborta.
        fell_back = False
        if action == "click" and not b.ev(f"!!document.querySelector({json.dumps(arg)})"):
            heur = classify_heuristic(snap)
            if heur != state and heur in NEXT_ACTION:
                fell_back = True
                state, action, arg = heur, *NEXT_ACTION[heur]
                gated = False
            else:
                action, arg = "wait", f"precondición ausente: {arg}"
                gated = True

        trace.append({"step": step, "state": state, "confidence": conf,
                      "action": action, "arg": arg, "gated": gated,
                      "fell_back": fell_back,
                      "t_snapshot_ms": round(t_snap), "t_classify_ms": round(t_cls),
                      "mode": mode})

        if not args.json:
            c = f"{conf:.2f}" if conf is not None else "  — "
            tag = " [GATE]" if gated else (" [FALLBACK-HEUR]" if fell_back else "")
            print(f"  paso {step:>2}  {state:<18} conf={c}  "
                  f"-> {action:<6} {arg or ''}{tag}   "
                  f"[snap {t_snap:.0f}ms + cls {t_cls:.0f}ms]")

        if action == "stop":
            break
        if action == "click":
            if not b.click(arg):
                trace[-1]["error"] = f"click falló: {arg}"
                break
        elif action == "wait":
            time.sleep(1.0)

    elapsed = time.time() - t_start
    b.close()

    summary = {
        "mode": args.mode,
        "steps": len(trace),
        "states": [t["state"] for t in trace],
        "elapsed_s": round(elapsed, 2),
        "total_classify_ms": sum(t["t_classify_ms"] for t in trace),
        "total_snapshot_ms": sum(t["t_snapshot_ms"] for t in trace),
        "reachou_content_resolved": any(t["state"] == "content_resolved" for t in trace),
        "gated_steps": sum(1 for t in trace if t.get("gated")),
        "heuristic_fallbacks": sum(1 for t in trace if t.get("fell_back")),
        "trace": trace,
    }
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"\n  {'ACEPTADO' if summary['reachou_content_resolved'] else 'NO LLEGÓ'}"
              f"  ·  {summary['steps']} pasos  ·  {summary['elapsed_s']}s  ·  "
              f"clasificación {summary['total_classify_ms']}ms  ·  "
              f"snapshot {summary['total_snapshot_ms']}ms  ·  "
              f"gated {summary['gated_steps']}  ·  "
              f"fallbacks {summary['heuristic_fallbacks']}  ·  modo={args.mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())