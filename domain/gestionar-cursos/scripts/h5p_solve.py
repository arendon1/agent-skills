"""
Solver genérico de contenidos interactivos H5P en Moodle (Aula Virtual Uniremington).

Reemplaza el approach de scripts one-off en /tmp. Objetivos de diseño (v2, 2026-09-14):

  1. IDEMPOTENCIA — ledger en `_cache/h5p_ledger_<course>.json`. Un contenido
     resuelto al 100% NUNCA se vuelve a resolver. Evita "rehacer el mismo
     trabajo un millón de veces".
  2. DERIVAR DEL CONTENIDO — el número de preguntas sale de `S.choices.length`
     (o del propio contenido), nunca de índices hardcodeados.
  3. ESPERA POR ESTADO — poll de la máquina de estados del H5P
     (`currentIndex`, `answered`, inputs visibles). Nunca `sleep` ciego.
  4. NO RECARGAR a mitad de run — `SingleChoiceSet` NO reanuda respuestas al
     recargar (a diferencia de `Blanks`): recargar destruye el progreso.
  5. CLICK IDEMPOTENTE — jamás clickear una alternativa ya `answered`.
  6. DESCONOCIDO != ADIVINAR — un tipo de tarea no soportado se registra como
     `tipo_no_soportado` y NO se fuerza.
  7. LECCIONES AUTOMÁTICAS — cada run anexa JSONL con métricas (clics, saltos
     idempotentes, tiempo, tipo, fricciones) a `references/h5p-lessons.jsonl`.
     `--report` las agrega y sugiere la siguiente optimización.

Uso:
    python3 h5p_solve.py --course-id 16564 --dest <curso> --surface surface:9
    python3 h5p_solve.py --course-id 16564 --dest <curso> --only 746509,774622
    python3 h5p_solve.py --course-id 16564 --dest <curso> --dry-run
    python3 h5p_solve.py --course-id 16564 --dest <curso> --report

Requiere: cmux CLI con una superficie de navegador ya autenticada en el Aula Virtual.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# Optional decision-layer guard. The shim is graceful: if absent, every call
# returns GuardVerdict(uncertain=True) and the orchestrator downgrades to the
# existing heuristic. Never raises; never breaks a run.
_JEV_SHIM = None
_USE_JEV_GUARD = False   # lo enciende main() con --use-jev-guard
try:
    _HERE_PY = Path(__file__).resolve().parent
    sys.path.insert(0, str(_HERE_PY))
    from jev_shim import jev_slide_done, jev_drag_safe, is_available as _is_jev_available  # type: ignore[import-not-found]
    _JEV_SHIM = {"available": _is_jev_available(), "slide_done": jev_slide_done, "drag_safe": jev_drag_safe}
except Exception:  # noqa: BLE001 — guardrailing the optional dep is the whole point
    def jev_slide_done(*_a, **_kw):
        return {"confident": False, "confident_done": False, "uncertain": True,
                "error_reason": "jev_shim_not_loaded", "mode": "fallback", "preset": None,
                "answers": {}, "cost_usd": 0.0, "latency_ms": 0, "raw": None}
    def jev_drag_safe(*_a, **_kw):
        return {"confident": False, "confident_done": False, "uncertain": True,
                "error_reason": "jev_shim_not_loaded", "mode": "fallback", "preset": None,
                "answers": {}, "cost_usd": 0.0, "latency_ms": 0, "raw": None}
    _JEV_SHIM = {"available": False, "slide_done": jev_slide_done, "drag_safe": jev_drag_safe}

CMUX = "/Applications/cmux.app/Contents/Resources/bin/cmux"
BASE = "https://aulavirtual.uniremington.edu.co"
SKILL_DIR = Path(__file__).resolve().parent.parent
LESSONS = SKILL_DIR / "references" / "h5p-lessons.jsonl"

CONTAINERS = {"H5P.CoursePresentation", "H5P.InteractiveVideo", "H5P.Column"}

# Navegadores abiertos en esta corrida. El `finally` global los cierra: sin eso cada ejecución
# dejaba su pestaña de Chrome viva (higiene exigida por Andrés, 2026-09-14).
_BROWSERS: list = []
_STATE = {"cdp_port": 9224}


def js(tpl: str, si: int | None = None, ci: int | None = None, **kw) -> str:
    """Sustituye placeholders __SI__/__CI__/__KEY__ sin pelear con las llaves de JS."""
    out = tpl.replace("__SI__", "" if si is None else str(si))
    out = out.replace("__CI__", "" if ci is None else str(ci))
    for k, v in kw.items():
        out = out.replace(f"__{k.upper()}__", str(v))
    return out


# --------------------------------------------------------------------------- #
# Transporte: cmux CLI                                                          #
# --------------------------------------------------------------------------- #
class Browser:
    """Cliente mínimo del navegador cmux (WKWebView), vía CLI."""

    def __init__(self, surface: str):
        self.surface = surface
        self.calls = 0

    def _run(self, *args: str) -> str:
        self.calls += 1
        p = subprocess.run([CMUX, "browser", "--surface", self.surface, *args],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"cmux {args[0]} falló: {p.stderr.strip()[:300]}")
        return p.stdout

    def goto(self, url: str) -> None:
        # Enfocar el webview ANTES de navegar. Un WKWebView en segundo plano queda
        # `visibilityState: hidden` y su navegación se suspende a mitad de carga (visto en vivo
        # 2026-09-14: 5 pestañas del mismo pane compartían un único slot visible y una de ellas
        # falló con `h5p_no_cargo` sobre un contenido intacto). Enfocar hace la navegación
        # autosuficiente; el requisito fuerte sigue siendo un PANE por superficie.
        try:
            self._run("focus-webview")
        except RuntimeError:
            pass                      # superficies sin foco (p. ej. headless) siguen funcionando
        self._run("goto", url)

    def ev(self, script: str):
        out = self._run("eval", "--script", script).strip()
        if not out:
            return None
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return {"_raw": out}

    def wait_for(self, script: str, timeout: float = 12.0, interval: float = 0.3, until=None):
        """
        Poll hasta que la condición se cumpla. Reemplaza los sleep ciegos.

        OJO: `until` es obligatorio-útil — un dict como {"ready": false} es truthy en
        Python, así que la verificación de verdad nunca puede ser `bool(last)` para
        los snippets que devuelven un objeto de estado. Se pasa un predicado explícito.
        Devuelve (segundos_hasta_cumplir | None, último_valor).
        """
        t0 = time.time()
        last = None
        while time.time() - t0 < timeout:
            last = self.ev(script)
            if (until(last) if until else bool(last)):
                return time.time() - t0, last
            time.sleep(interval)
        return None, last


# --------------------------------------------------------------------------- #
# Transporte alternativo: Chrome real vía CDP                                   #
# --------------------------------------------------------------------------- #
class ChromeBrowser:
    """
    Chrome real vía DevTools Protocol, sobre el perfil AUTORIZADO de Moodle
    (`~/.agents/.browserdata`).

    Por qué existe (pedido de Andrés, 2026-09-14): Chrome carga TODAS sus pestañas
    aunque no tengan foco, así que se puede fan-out en paralelo sin `focus-webview` y
    sin el fallo `surface_throttled_segundo_plano` que sí sufre la WKWebView de cmux
    (donde N pestañas del mismo pane comparten un único slot visible).

    Misma interfaz que `Browser` (goto/ev/wait_for/calls) para que los solvers no cambien.
    """

    def __init__(self, port: int, url: str = "about:blank", target_id: str | None = None,
                 reuse: bool = True):
        import websocket

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import navegador_cdp as cdp

        self.port = port
        self.calls = 0
        self.reused = False
        # Guard de perfil: NUNCA operar un Chrome cuyo perfil no esté en la allowlist.
        perfil = cdp.perfil_de_puerto(port)
        if perfil is None:
            raise RuntimeError(f"no hay endpoint CDP vivo en el puerto {port}")
        perfil = cdp._normalize_profile(perfil)
        if not cdp.is_authorized(perfil):
            raise RuntimeError(f"perfil Chrome NO autorizado en el puerto {port}: {perfil}")
        self.perfil = perfil

        if target_id:
            self.target = {"id": target_id}
            self._created = False
        else:
            # REUSAR antes de crear (pedido de Andrés, 2026-09-14): crear una pestaña por
            # operación deja huérfanas. Si ya hay una pestaña del Aula Virtual, se adopta.
            # OJO: en fan-out en paralelo cada agente necesita la SUYA -> `reuse=False`.
            adoptada = _pestana_reutilizable(port) if reuse else None
            if adoptada:
                self.target = adoptada
                self._created = False
                self.reused = True
            else:
                self.target = _cdp_http(port, "/json/new?" + urllib.parse.quote(url, safe=""), "PUT")
                self._created = True
                if not isinstance(self.target, dict) or not self.target.get("id"):
                    raise RuntimeError(f"no se pudo abrir pestaña: {str(self.target)[:200]}")
        self._ws_url = (self.target.get("webSocketDebuggerUrl")
                        or f"ws://127.0.0.1:{port}/devtools/page/{self.target['id']}")
        self._ws = websocket.create_connection(self._ws_url, timeout=30, suppress_origin=True)
        self._id = 0
        for metodo in ("Page.enable", "Runtime.enable"):
            self._cmd(metodo)
        # Con `reuse` la pestaña ya existía: el `url` del constructor NO se aplicaba (solo se usaba
        # al crear), así que el consumidor quedaba en la página vieja sin darse cuenta. Ahora el
        # contrato es el mismo en ambos casos: al salir del constructor se está en `url`.
        if url and url != "about:blank":
            actual = self.ev("(()=>{return JSON.stringify({u: location.href})})()") or {}
            if actual.get("u") != url:
                self.goto(url)

    def _cmd(self, method: str, params: dict | None = None) -> dict:
        self.calls += 1
        self._id += 1
        mid = self._id
        self._ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self._ws.recv())
            if msg.get("id") == mid:
                return msg

    def goto(self, url: str) -> None:
        self._cmd("Page.navigate", {"url": url})
        # Chrome no necesita foco para cargar: solo hay que esperar el documento.
        self.wait_for("(()=>{return JSON.stringify({r: document.readyState})})()",
                      timeout=25, interval=0.4,
                      until=lambda r: r and r.get("r") in ("interactive", "complete"))

    def ev(self, script: str):
        msg = self._cmd("Runtime.evaluate", {"expression": script, "returnByValue": True,
                                             "awaitPromise": False, "userGesture": True})
        res = msg.get("result") or {}
        if res.get("exceptionDetails"):
            return {"_error": str(res["exceptionDetails"].get("text"))[:200]}
        inner = res.get("result") or {}
        val = inner.get("value")
        if isinstance(val, str):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return {"_raw": val}
        return val

    def wait_for(self, script: str, timeout: float = 12.0, interval: float = 0.3, until=None):
        t0 = time.time()
        last = None
        while time.time() - t0 < timeout:
            last = self.ev(script)
            if (until(last) if until else bool(last)):
                return time.time() - t0, last
            time.sleep(interval)
        return None, last

    def close(self, close_tab: bool | None = None) -> None:
        """
        Cierra el WebSocket Y LA PESTAÑA que este objeto abrió.

        Higiene exigida por Andrés (2026-09-14): antes `close()` solo cerraba el WebSocket, así que
        cada corrida/probe dejaba su pestaña viva. 20+ probes = 20+ pestañas huérfanas. Si la
        pestaña llegó por `target_id` NO se cierra: no la abrimos nosotros. `_keep_tab` la preserva
        a pedido (diagnóstico).
        """
        if close_tab is None:
            close_tab = self._created and not getattr(self, "_keep_tab", False)
        try:
            self._ws.close()
        except Exception:
            pass
        if close_tab:
            try:
                _cdp_http(self.port, f"/json/close/{self.target['id']}")
            except Exception:
                pass
            self._created = False


def _cdp_http(port: int, path: str, method: str = "GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"_raw": body[:200]}


def pestanas_abiertas(port: int = 9224) -> list:
    """Pestañas (type=page) vivas en el Chrome del puerto dado."""
    data = _cdp_http(port, "/json/list")
    if not isinstance(data, list):
        return []
    return [t for t in data if isinstance(t, dict) and t.get("type") == "page"]


def cerrar_pestanas_huerfanas(port: int = 9224, conservar: int = 0) -> dict:
    """
    Cierra pestañas huérfanas de corridas anteriores.

    Solo toca URLs del Aula Virtual (Moodle): NUNCA pestañas del usuario en otros sitios. `conservar`
    deja vivas las primeras N que coincidan (útil si el usuario tiene el informe abierto a propósito).
    """
    patrones = ("/mod/hvp/view.php", "/grade/report/", "/course/view.php", "/mod/hvp/report")
    cerradas, vistas, conservadas = [], 0, []
    for t in pestanas_abiertas(port):
        u = t.get("url", "")
        if not any(p in u for p in patrones):
            continue
        vistas += 1
        if vistas <= conservar:
            conservadas.append(u[:70])
            continue
        _cdp_http(port, f"/json/close/{t.get('id')}")
        cerradas.append(u[:70])
    return {"cerradas": cerradas, "conservadas": conservadas}


def _pestana_reutilizable(port: int = 9224, dominio: str = "aulavirtual.uniremington.edu.co"):
    """
    Primera pestaña ya abierta del Aula Virtual, para ADOPTARLA en vez de crear otra.

    Reusar es más barato y evita la fuga de pestañas; solo se adopta si la pestaña NO está siendo
    manejada por otra corrida (por eso el fan-out en paralelo pide `reuse=False`).
    """
    for t in pestanas_abiertas(port):
        if dominio in (t.get("url") or ""):
            return t
    return None


def _h5p_iframe_js(si: int, ci: int | None = None) -> str:
    """Placeholder para futuros snippets; hoy los solvers usan window[0]."""
    return ""


# --------------------------------------------------------------------------- #
# Snippets JS (el DOM H5P vive en el iframe, accesible vía window[0])            #
# --------------------------------------------------------------------------- #
JS_MAP = r"""
(()=>{
  const w = window[0];
  if (!w || !w.H5P || !w.H5P.instances || !w.H5P.instances.length)
    return JSON.stringify({ready: false});
  const out = [];
  w.H5P.instances.forEach((I, idx) => {
    const info = I.libraryInfo;
    const o = {idx, machine: info ? info.machineName : '?',
               lib: info ? info.machineName + ' ' + info.versionMajor + '.' + info.versionMinor : '?',
               contentId: I.contentId,
               score: I.getScore ? I.getScore() : 0,
               max: I.getMaxScore ? I.getMaxScore() : 0, tasks: []};
    if (I.children) {
      o.children_slides = I.children.length;
    }
    // OJO: CP.slides incluye el slide de RESUMEN y CP.children NO. Contar por children
    // dejaba el deck en 12/13 y nunca se llegaba al botón de chequeo final (fallo real
    // señalado por Andrés el 2026-09-14). El total autoritativo es CP.slides.length.
    o.slides = I.slides ? I.slides.length : (I.children ? I.children.length : 0);
    if (I.children) {
      o.tasks = [];
      I.children.forEach((sl, si) => {
        (sl.children || []).forEach((c, ci) => {
          const ins = c.instance;
          const mn = ins && ins.libraryInfo && ins.libraryInfo.machineName;
          if (!mn) return;
          if (/^H5P\.(Image|AdvancedText|Video|Audio|Table|Link|Shape|Text|ImageHotspots)/.test(mn)) return;
          o.tasks.push({slide: si, child: ci, machine: mn,
                        score: ins.getScore ? ins.getScore() : null,
                        max: ins.getMaxScore ? ins.getMaxScore() : null});
        });
      });
    }
    out.push(o);
  });
  return JSON.stringify({ready: true, instances: out});
})()
"""

# Selector del DOM de cada tarea, usado para anclar el readiness AL SLIDE OBJETIVO.
# Sin esto, al saltar 5→6 el DOM del slide anterior sigue visible y se rellenaba el slide
# equivocado (bug real observado 2026-09-14: corrompía el slide 5 al resolver el 6).
TASK_SELECTOR = {
    "H5P.Blanks": ".h5p-blanks input.h5p-text-input",
    "H5P.SingleChoiceSet": ".h5p-sc-alternative",
    "H5P.MultiChoice": ".h5p-answer",
    "H5P.TrueFalse": ".h5p-true-false-answer",
    "H5P.DragQuestion": ".h5p-dragquestion .ui-draggable",
    "H5P.MarkTheWords": ".h5p-mark-the-words span",
}

JS_TASK_READY = r"""
(()=>{
  const CP = window[0].H5P.instances[0], d = window[0].document;
  const si = __SI__;
  if (typeof CP.getCurrentSlideIndex === 'function' && CP.getCurrentSlideIndex() !== si)
    return JSON.stringify({ok: false, why: 'otro-slide'});
  // Anclaje por CLASE, no por posición: `querySelectorAll('.h5p-slide')[si]` puede desalinearse
  // (el deck tiene 13 .h5p-slide pero CP.children solo 12). El slide actual es inequívoco.
  const slide = d.querySelector('.h5p-slide.h5p-current');
  if (!slide) return JSON.stringify({ok: false, why: 'sin-slide'});
  const vis = Array.from(slide.querySelectorAll('__SEL__'))
                   .filter(e => e.getClientRects().length > 0);
  return JSON.stringify({ok: vis.length > 0, n: vis.length, why: vis.length ? 'ok' : 'oculto'});
})()
"""

# Igual que JS_TASK_READY pero exigiendo además que la CLASE DOM del slide actual coincida
# (el índice interno se actualiza antes que la clase: ver `goto_slide`).
JS_TASK_READY_DOM = r"""
(()=>{
  const CP = window[0].H5P.instances[0], d = window[0].document;
  const si = __SI__;
  const els = Array.from(d.querySelectorAll('.h5p-slide'));
  const cur = d.querySelector('.h5p-slide.h5p-current');
  if (!cur || els.indexOf(cur) !== si) return JSON.stringify({ok: false, why: 'clase-dom-otro-slide'});
  const vis = Array.from(cur.querySelectorAll('__SEL__')).filter(e => e.getClientRects().length > 0);
  return JSON.stringify({ok: vis.length > 0, n: vis.length});
})()
"""

# Tareas REALES del slide actual, resueltas DESPUÉS de que el slide renderiza.
# Los hijos con `libraryInfo` nulo NO se descartan en silencio: se clasifican. Los
# `h5p-press-to-go` son hotspots de navegación (no tareas); cualquier otro nodo sin tipo
# se reporta como `nodos_no_clasificados` para que nada se pierda por omisión.
JS_SLIDE_TASKS = r"""
(()=>{
  const CP = window[0].H5P.instances[0];
  const si = __SI__;
  // El slide de resumen no está en CP.children: no tiene tareas, pero SÍ hay que visitarlo.
  const sl = CP.children[si] || {children: []};
  const tasks = [], unknown = [];
  let nav = 0;
  (sl.children || []).forEach((c, i) => {
    const ins = c.instance;
    const mn = (ins && ins.libraryInfo && ins.libraryInfo.machineName)
            || (c.libraryInfo && c.libraryInfo.machineName) || null;
    if (!mn) {
      let cls = '';
      try { cls = (ins && ins.$element && ins.$element[0]) ? ins.$element[0].className : ''; } catch (e) {}
      if (/press-to-go|h5p-link|h5p-visible|advancetext/.test(cls) || cls === '') nav++;
      else unknown.push({i, cls});
      return;
    }
    if (/^H5P\.(Image|AdvancedText|Table|Video|Audio|Shape|Link|Text|ImageHotspots)/.test(mn)) return;
    tasks.push({slide: si, child: i, machine: mn});
  });
  return JSON.stringify({si, cur: CP.getCurrentSlideIndex ? CP.getCurrentSlideIndex() : null,
                         tasks, nav, unknown});
})()
"""

JS_JUMP = "(()=>{const CP=window[0].H5P.instances[0];CP.jumpToSlide(__SI__);return JSON.stringify({ok:true});})()"

# Estado de navegación, para CONFIRMAR que el salto ocurrió de verdad.
JS_SLIDE_STATE = r"""
(()=>{
  const CP = window[0].H5P.instances[0];
  const d = window[0].document;
  const total = CP.slides ? CP.slides.length : (CP.children || []).length;
  const cur = CP.getCurrentSlideIndex ? CP.getCurrentSlideIndex() : null;
  const el = d.querySelector('.h5p-slide.h5p-current');
  const els = Array.from(d.querySelectorAll('.h5p-slide'));
  return JSON.stringify({cur, total, currentDomIndex: el ? els.indexOf(el) : null});
})()
"""

JS_FINISH = r"""
(()=>{
  const H = window[0].H5P;
  const I = H.instances[0];
  // Cerrar NO es solo postear el score: el deck debe quedar recorrido hasta el final.
  // El índice del último slide sale de CP.slides (incluye el resumen), no de children.
  let lastSlide = null;
  try {
    const total = I.slides ? I.slides.length : (I.children || []).length;
    if (total && typeof I.jumpToSlide === 'function') {
      lastSlide = total - 1;
      I.jumpToSlide(lastSlide);
    }
  } catch (e) {}
  const s = I.getScore ? I.getScore() : 0, m = I.getMaxScore ? I.getMaxScore() : 0;
  const res = {contentId: I.contentId, score: s, max: m, lastSlide,
               enUltimoSlide: I.getCurrentSlideIndex ? I.getCurrentSlideIndex() : null};
  try { H.setFinished(I.contentId, s, m); res.setFinished = 'ok'; }
  catch (e) { res.setFinished = 'ERR:' + e.message; }
  try {
    if (I.triggerXAPIScored) { I.triggerXAPIScored(s, m, 'completed', true, 1); res.xapi = 'ok'; }
  } catch (e) { res.xapi = 'ERR:' + e.message; }
  return JSON.stringify(res);
})()
"""

JS_PREFLIGHT = r"""
(()=>{
  // Diagnóstico cuando el H5P no aparece. Un WKWebView en segundo plano se suspende:
  // visibilityState 'hidden' + readyState 'loading' = navegación a medias, NO un fallo del H5P.
  const d = document;
  return JSON.stringify({
    visibility: d.visibilityState, hidden: d.hidden, readyState: d.readyState,
    iframes: d.querySelectorAll('iframe').length,
    w0: !!window[0], w0H5P: !!(window[0] && window[0].H5P)
  });
})()
"""

JS_XAPI_POSTED = r"""
(()=>{
  const hits = performance.getEntriesByType('resource')
    .filter(r => /ajax\.php[^ ]*xapiresult/.test(r.name)).length;
  return JSON.stringify({hits});
})()
"""

# --- Blanks ----------------------------------------------------------------- #
JS_BLANKS_INFO = r"""
(()=>{
  const B = window[0].H5P.instances[0].children[__SI__].children[__CI__].instance;
  const q = (B.params.questions || [])[0];
  const t = (typeof q === 'string') ? q : ((q && q.text) || '');
  const sols = (t.match(/\*[^*]+\*/g) || []).map(s => s.slice(1, -1));
  const s = B.getScore ? B.getScore() : 0, m = B.getMaxScore ? B.getMaxScore() : 0;
  return JSON.stringify({sols, score: s, max: m, answered: (m > 0 && s === m)});
})()
"""

JS_BLANKS_FILL = r"""
(()=>{
  const B = window[0].H5P.instances[0].children[__SI__].children[__CI__].instance;
  const q = (B.params.questions || [])[0];
  const t = (typeof q === 'string') ? q : ((q && q.text) || '');
  const vals = (t.match(/\*[^*]+\*/g) || []).map(s => s.slice(1, -1));
  const d = window[0].document;
  // ANCLADO AL SLIDE ACTUAL por clase (no por índice): solo los inputs de este slide.
  const slide = d.querySelector('.h5p-slide.h5p-current');
  const inputs = slide
    ? Array.from(slide.querySelectorAll('.h5p-blanks input.h5p-text-input'))
            .filter(i => i.getClientRects().length > 0)
    : [];
  // INVARIANTE: nº de inputs visibles == nº de huecos declarados. Si no coincide,
  // NO se escribe ni se comprueba: antes corrompía el slide previo.
  if (inputs.length !== vals.length)
    return JSON.stringify({mismatch: true, nInputs: inputs.length, expected: vals.length});
  const setter = Object.getOwnPropertyDescriptor(window[0].HTMLInputElement.prototype, 'value').set;
  inputs.forEach((inp, i) => {
    setter.call(inp, vals[i] || '');
    inp.dispatchEvent(new window[0].Event('input', {bubbles: true}));
    inp.dispatchEvent(new window[0].Event('change', {bubbles: true}));
  });
  return JSON.stringify({vals, nInputs: inputs.length});
})()
"""

JS_BLANKS_READY = r"""
(()=>{
  const d = window[0].document;
  const slide = d.querySelector('.h5p-slide.h5p-current');
  if (!slide) return JSON.stringify({ready: false});
  const has = Array.from(slide.querySelectorAll('.h5p-blanks input.h5p-text-input'))
                 .some(i => i.getClientRects().length > 0 && i.value);
  const btn = Array.from(slide.querySelectorAll('button.h5p-question-check-answer'))
                  .some(x => x.getClientRects().length > 0);
  return JSON.stringify({ready: has && btn});
})()
"""

JS_CLICK_CHECK = r"""
(()=>{
  const d = window[0].document;
  const slide = d.querySelector('.h5p-slide.h5p-current');
  const scope = slide || d;
  const b = Array.from(scope.querySelectorAll('button.h5p-question-check-answer'))
                 .find(x => x.getClientRects().length > 0);
  if (!b) return JSON.stringify({clicked: false});
  b.click();
  return JSON.stringify({clicked: true});
})()
"""

# --- Chequeo FINAL del deck --------------------------------------------------- #
# El último slide del CoursePresentation es `.h5p-summary-slide` y su botón
# `.h5p-show-solutions` ("Mostrar solución") es el que cierra el intento. Sin ese clic el
# deck queda a medias (p. ej. 5/13) aunque todos los quizzes estén al 100%.
JS_FINAL_STATE = r"""
(()=>{
  const CP = window[0].H5P.instances[0];
  const d = window[0].document;
  const total = CP.slides ? CP.slides.length : (CP.children || []).length;
  const cur = CP.getCurrentSlideIndex ? CP.getCurrentSlideIndex() : null;
  const sl = d.querySelectorAll('.h5p-slide')[cur];
  const btn = d.querySelector('.h5p-show-solutions');
  return JSON.stringify({
    total, cur,
    isSummary: !!(sl && /h5p-summary-slide/.test(sl.className)),
    isSolutionMode: !!CP.isSolutionMode,
    botonFinal: btn ? {vis: btn.getClientRects().length > 0, cls: (btn.className || '').slice(0, 60)} : null,
    resumen: sl ? (sl.innerText || '').replace(/\s+/g, ' ').slice(0, 220) : null,
    score: CP.getScore ? CP.getScore() : null, max: CP.getMaxScore ? CP.getMaxScore() : null
  });
})()
"""

JS_CLICK_FINAL = r"""
(()=>{
  const d = window[0].document;
  const b = Array.from(d.querySelectorAll('.h5p-show-solutions'))
                 .find(x => x.getClientRects().length > 0);
  if (!b) return JSON.stringify({clicked: false});
  b.click();
  return JSON.stringify({clicked: true, label: (b.textContent || '').trim().slice(0, 30)});
})()
"""

JS_TASK_SCORE = r"""
(()=>{
  const T = window[0].H5P.instances[0].children[__SI__].children[__CI__].instance;
  return JSON.stringify({score: T.getScore ? T.getScore() : null,
                         max: T.getMaxScore ? T.getMaxScore() : null});
})()
"""

# --- SingleChoiceSet -------------------------------------------------------- #
JS_SCS_STATE = r"""
(()=>{
  const S = window[0].H5P.instances[0].children[__SI__].children[__CI__].instance;
  const cur = S.currentIndex, total = (S.choices || []).length;
  const answered = !!(S.choices && S.choices[cur] && S.choices[cur].answered);
  return JSON.stringify({cur, total, answered, done: cur >= total,
    score: S.getScore ? S.getScore() : 0, max: S.getMaxScore ? S.getMaxScore() : 0,
    corrects: S.results ? S.results.corrects : null,
    wrongs: S.results ? S.results.wrongs : null});
})()
"""

JS_SCS_ADVANCED = r"""
(()=>{
  const S = window[0].H5P.instances[0].children[__SI__].children[__CI__].instance;
  // ÍNDICE SOLAMENTE. `S.choices[cur].answered` NO sirve como señal de avance:
  // se pone en true al instante pero el índice tarda segundos en avanzar, y el
  // restaurar userResponses puede dejar `answered` en true sin avance real.
  return JSON.stringify({ok: S.currentIndex > __CUR__});
})()
"""

JS_SCS_CONTINUE = r"""
(()=>{
  const d = window[0].document;
  const slide = d.querySelector('.h5p-slide.h5p-current');
  if (!slide) return JSON.stringify({clicked: false});
  const b = Array.from(slide.querySelectorAll('button, .h5p-joubelui-button'))
                 .filter(x => x.getClientRects().length > 0)
                 .find(x => /continuar|siguiente|continue|next/i.test(x.textContent || ''));
  if (!b) return JSON.stringify({clicked: false});
  b.click();
  return JSON.stringify({clicked: true, text: (b.textContent || '').trim().slice(0, 30)});
})()
"""

JS_SCS_CLICK = r"""
(()=>{
  const d = window[0].document;
  const slide = d.querySelector('.h5p-slide.h5p-current');
  if (!slide) return JSON.stringify({clicked: false, why: 'sin-slide-actual'});
  const alts = Array.from(slide.querySelectorAll('.h5p-sc-alternative.h5p-sc-is-correct'))
                    .filter(a => a.getClientRects().length > 0);
  if (!alts.length) return JSON.stringify({clicked: false, why: 'sin-alternativa-correcta'});
  alts[0].click();
  return JSON.stringify({clicked: true, text: alts[0].textContent.trim().slice(0, 70)});
})()
"""

# --- Question (MultiChoice / TrueFalse / MarkTheWords) ---------------------- #
JS_ANSWER_QUESTION = r"""
(()=>{
  const Q = window[0].H5P.instances[0].children[__SI__].children[__CI__].instance;
  const d = window[0].document.querySelector('.h5p-slide.h5p-current');
  if (!d) return JSON.stringify({answered: false, unsupported: true, why: 'sin-slide-actual'});
  if (Q.getScore && Q.getMaxScore && Q.getMaxScore() > 0 && Q.getScore() === Q.getMaxScore())
    return JSON.stringify({answered: true, done: true});
  const mc = (Q.params && Q.params.answers) ? Q.params.answers : null;
  const tf = (Q.params && typeof Q.params.correct !== 'undefined') ? Q.params.correct : null;
  let clicked = 0;
  if (mc) {
    mc.forEach((a, i) => {
      if (!a.correct) return;
      const el = d.querySelector('.h5p-answer[data-id="' + i + '"] .h5p-alternative-container');
      if (el && el.getClientRects().length > 0) { el.click(); clicked++; }
    });
  } else if (tf !== null) {
    const want = String(tf);
    const el = Array.from(d.querySelectorAll('.h5p-true-false-answer'))
                   .find(x => (x.getAttribute('data-value') || '').toLowerCase() === want
                              && x.getClientRects().length > 0);
    if (el) { el.click(); clicked++; }
  } else { return JSON.stringify({answered: false, unsupported: true}); }
  return JSON.stringify({answered: true, clicked});
})()
"""

# --- DragQuestion ----------------------------------------------------------- #
JS_DRAGQ_SOLVE = r"""
(()=>{
  const DQ = window[0].H5P.instances[0].children[__SI__].children[__CI__].instance;
  const n = (DQ.draggables || []).length;
  if (!n) return JSON.stringify({answered: false, note: 'no draggables (slide no visible)'});
  let placed = 0, errors = 0;
  for (let di = 0; di < n; di++) {
    const el = DQ.draggables[di];
    if (el.dropZone !== undefined && el.dropZone !== -1) continue;
    const dz = DQ.correctDZs && DQ.correctDZs[di];
    const target = Array.isArray(dz) ? dz[0] : dz;
    if (target === undefined || target === null) { errors++; continue; }
    try { el.addToDropZone(0, el, target); placed++; } catch (e) { errors++; }
  }
  return JSON.stringify({answered: true, placed, errors,
    score: DQ.getScore ? DQ.getScore() : null, max: DQ.getMaxScore ? DQ.getMaxScore() : null});
})()
"""

# --- Página del curso ------------------------------------------------------- #
JS_COURSE_H5P = r"""
(()=>{
  const out = [];
  document.querySelectorAll('li.activity.modtype_hvp').forEach(li => {
    const a = li.querySelector('a[href*="/mod/hvp/view.php"]');
    if (!a) return;
    const b = li.querySelector('[data-action="toggle-manual-completion"]');
    out.push({
      id: a.href.match(/id=(\d+)/)[1],
      name: (a.querySelector('.instancename') || a).textContent.trim().slice(0, 80),
      done: !!b && b.getAttribute('data-toggletype') === 'manual:undo'
    });
  });
  return JSON.stringify(out);
})()
"""

# --- Informe de calificaciones: fuente AUTORITATIVA de qué hay y qué falta --------- #
# La lista de actividades de la página del curso OMITE contenidos H5P (en el curso 16564 veía 6
# de 12). El informe (`grade/report/user`) es donde Andrés verifica y muestra la nota en escala
# 0-10: "10,00" = resuelto al 100%; "-" = nunca intentado. Sirve a la vez como plan y como
# verificación final.
JS_GRADE_H5P = r"""
(()=>{
  const out = [];
  document.querySelectorAll('table tbody tr').forEach(tr => {
    const tds = Array.from(tr.querySelectorAll('th,td'));
    if (!tds.length) return;
    const cell = tds[0];
    const txt = cell.innerText.replace(/\s+/g, ' ').trim();
    if (!/CONTENIDO INTERACTIVO/i.test(txt)) return;
    const a = cell.querySelector('a');
    const href = a ? a.getAttribute('href') : null;
    const mm = href ? href.match(/[?&]id=(\d+)/) : null;
    if (!mm) return;
    out.push({
      id: mm[1],
      nombre: txt.replace(/^CONTENIDO INTERACTIVO\s*/i, '').slice(0, 90),
      calificacion: ((tds[2] || {}).innerText || '').trim(),
      pct: ((tds[4] || {}).innerText || '').trim()
    });
  });
  return JSON.stringify(out);
})()
"""

JS_MARK_DONE = r"""
(()=>{
  const b = document.querySelector('[data-action="toggle-manual-completion"][data-cmid="__ID__"]');
  if (!b) return JSON.stringify({err: 'no-button'});
  if (b.getAttribute('data-toggletype') === 'manual:undo') return JSON.stringify({already: true});
  b.click();
  return JSON.stringify({clicked: true});
})()
"""


# --------------------------------------------------------------------------- #
# Ledger — la memoria que evita rehacer trabajo                                 #
# --------------------------------------------------------------------------- #
def ledger_path(course_id: str, dest: Path | None) -> Path:
    cache = (dest or Path.cwd()) / "_cache"
    # parents=True: con `--dest /tmp/lo-que-sea` la ruta puede no existir.
    # Bug real detectado por 2 agentes en paralelo (2026-09-14): sin parents el solver
    # moría con FileNotFoundError antes de resolver nada.
    cache.mkdir(parents=True, exist_ok=True)
    return cache / f"h5p_ledger_{course_id}.json"


def load_ledger(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"course": None, "updated": None, "activities": {}}


def save_ledger(path: Path, led: dict) -> None:
    led["updated"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Solvers                                                                      #
# --------------------------------------------------------------------------- #
def solve_blanks(b: Browser, si: int, ci: int, m: dict) -> dict:
    info = b.ev(js(JS_BLANKS_INFO, si, ci)) or {}
    if info.get("answered"):
        m["skipped_tasks"] += 1
        return {"type": "Blanks", "slide": si, "score": info.get("score"),
                "max": info.get("max"), "note": "ya respondido"}
    n = len(info.get("sols") or [])
    if not n:
        m["opportunities"].append("blanks_sin_soluciones_en_params")
        return {"type": "Blanks", "slide": si, "unsupported": True}
    filled = b.ev(js(JS_BLANKS_FILL, si, ci)) or {}
    if filled.get("mismatch"):          # invariante roto: NO se comprueba, no se corrompe nada
        m["opportunities"].append("blanks_input_mismatch")
        return {"type": "Blanks", "slide": si, "unsupported": True,
                "nInputs": filled.get("nInputs"), "esperados": filled.get("expected")}
    b.ev(js(JS_BLANKS_FILL, si, ci))
    b.wait_for(js(JS_BLANKS_READY, si, ci), timeout=6, until=lambda r: r and r.get("ready"))
    b.ev(js(JS_CLICK_CHECK, si=si))
    m["clicks"] += n
    _, st = b.wait_for(js(JS_TASK_SCORE, si, ci), timeout=8,
                       until=lambda r: r and r.get("max") and r.get("score") == r.get("max"))
    st = st or {}
    if st.get("max") and st.get("score") != st.get("max"):
        m["opportunities"].append("blanks_score_parcial")
    return {"type": "Blanks", "slide": si, "score": st.get("score"), "max": st.get("max"),
            "huecos": n}


def solve_scs(b: Browser, si: int, ci: int, m: dict, max_clicks: int = 16) -> dict:
    """
    SingleChoiceSet. Reglas derivadas de observación (no de suposiciones):
      · el total sale de `S.choices.length`;
      · el avance se detecta SOLO por `currentIndex` (nunca por `.answered`);
      · clickear una alternativa ya respondida es idempotente → no hay que protegerlo;
      · tras clickear, el índice tarda ~2s en avanzar; si stall 3× se reporta, no se cuelga.
    """
    _, st = b.wait_for(js(JS_SCS_STATE, si, ci), timeout=10,
                       until=lambda r: r and r.get("total"))
    st = st or {}
    total = st.get("total") or 0
    if not total:
        m["opportunities"].append("scs_total_no_derivable")
        return {"type": "SingleChoiceSet", "slide": si, "unsupported": True}
    if st.get("max") and st.get("score") == st.get("max"):
        m["skipped_tasks"] += 1
        return {"type": "SingleChoiceSet", "slide": si, "score": st.get("score"),
                "max": st.get("max"), "note": "ya respondido"}

    last_cur = st.get("cur", 0)
    clicks, stall, pasos = 0, 0, 0
    while clicks < max_clicks:
        st = b.ev(js(JS_SCS_STATE, si, ci)) or {}
        cur = st.get("cur", 0)
        if cur >= total:
            break
        if cur > last_cur:
            last_cur, stall = cur, 0
        r = b.ev(js(JS_SCS_CLICK, si, ci)) or {}
        if not r.get("clicked"):
            stall += 1
            if stall >= 3:
                m["opportunities"].append(
                    "scs_sin_alternativa_correcta:" + str(r.get("why")))
                break
            time.sleep(0.6)
            pasos += 1
            continue
        clicks += 1
        m["clicks"] += 1
        took, _ = b.wait_for(js(JS_SCS_ADVANCED, si, ci, cur=cur), timeout=7,
                             until=lambda x: x and x.get("ok"), interval=0.7)
        if took is None:
            stall += 1
            if stall == 1:
                # algunos SCS no auto-avanzan: pueden requerir "Continuar"
                b.ev(js(JS_SCS_CONTINUE, si=si))
            if stall >= 3:
                m["opportunities"].append("scs_sin_avance")
                break
            time.sleep(0.6)
        else:
            stall = 0
        pasos += 1

    st = b.ev(js(JS_SCS_STATE, si, ci)) or {}
    if st.get("max") and st.get("score") != st.get("max"):
        m["opportunities"].append("scs_score_parcial")
    return {"type": "SingleChoiceSet", "slide": si, "score": st.get("score"),
            "max": st.get("max"), "preguntas": total, "correctas": st.get("corrects"),
            "errores": st.get("wrongs"), "clicks": clicks, "pasos": pasos}


def solve_question(b: Browser, si: int, ci: int, m: dict) -> dict:
    r = b.ev(js(JS_ANSWER_QUESTION, si, ci)) or {}
    if r.get("unsupported"):
        m["opportunities"].append("question_params_inesperados")
        return {"type": "Question", "slide": si, "unsupported": True}
    if r.get("done"):
        m["skipped_tasks"] += 1
    m["clicks"] += r.get("clicked", 0)
    b.wait_for(js(JS_BLANKS_READY, si, ci), timeout=5, until=lambda x: x and x.get("ready"))
    b.ev(js(JS_CLICK_CHECK, si=si))
    _, st = b.wait_for(js(JS_TASK_SCORE, si, ci), timeout=8,
                       until=lambda x: x and x.get("max") and x.get("score") == x.get("max"))
    st = st or {}
    if st.get("max") and st.get("score") != st.get("max"):
        m["opportunities"].append("question_score_parcial")
    return {"type": "MultiChoice/TrueFalse", "slide": si, "score": st.get("score"),
            "max": st.get("max")}


def solve_dragq(b: Browser, si: int, ci: int, m: dict) -> dict:
    r = b.ev(js(JS_DRAGQ_SOLVE, si, ci)) or {}
    if r.get("note"):
        m["opportunities"].append("dragq_slide_no_visible")
        return {"type": "DragQuestion", "slide": si, "unsupported": True}
    m["clicks"] += r.get("placed", 0)
    if r.get("errors"):
        m["opportunities"].append("dragq_placement_parcial")
    b.ev(js(JS_CLICK_CHECK, si=si))
    _, st = b.wait_for(js(JS_TASK_SCORE, si, ci), timeout=8,
                       until=lambda x: x and x.get("max") and x.get("score") == x.get("max"))
    st = st or {}
    if st.get("max") and st.get("score") != st.get("max"):
        m["opportunities"].append("dragq_score_parcial")
    return {"type": "DragQuestion", "slide": si, "score": st.get("score"), "max": st.get("max")}


# El registro de solvers vive DESPUÉS de las funciones (antes estaba antes y referenciar
# `solve_findthewords` daba NameError en import).


def goto_slide(b: Browser, si: int, m: dict | None = None, attempts: int = 6,
               per_attempt: float = 3.0) -> bool:
    """
    Salta al slide `si` y CONFIRMA que se llegó.

    `CP.jumpToSlide(i)` se IGNORA EN SILENCIO si se pide mientras la transición anterior sigue
    en curso (visto en vivo 2026-09-14: los slides impares del deck nunca se alcanzaban; el
    índice quedaba en el par anterior, la tarea no estaba en el DOM y el solver abortaba con
    "n inputs == 0"). Por eso hay que re-emitir el salto hasta que el índice cambie de verdad:
    esperar no alcanza, hay que volver a pedirlo.
    """
    for _ in range(attempts):
        b.ev(js(JS_JUMP, si=si))
        # Confirmar las DOS cosas: el índice interno Y la clase DOM del slide actual.
        # `CP.getCurrentSlideIndex()` se actualiza ANTES de que `.h5p-current` se mueva, así que
        # confirmar solo el índice dejaba los selectores scoped al slide ANTERIOR: en vivo, al
        # pedir el slide 6 se leyeron los 3 inputs del slide 5 (`nInputs 3 / esperados 2`) y la
        # invariante abortó. La clase DOM es la que manda para cualquier query por selector.
        took, _st = b.wait_for(
            JS_SLIDE_STATE, timeout=per_attempt,
            until=lambda r: r and r.get("cur") == si and r.get("currentDomIndex") == si)
        if took is not None:
            return True
    if m is not None:
        m["opportunities"].append(f"salto_ignorado:{si}")
    return False


def plan_deck(n_slides: int, prescan: list, full_walk: bool = False) -> list:
    """
    Slides a visitar: SOLO los que tienen actividad + el slide de resumen.

    Optimización pedida por Andrés (2026-09-14): si las actividades están en 2 de 13 slides y el
    chequeo final vive en el último, recorrer los 13 es desperdicio puro (~40s y ~200 llamadas
    contra ~15s y ~70). El plan NO es una suposición sobre el contenido: sale del pre-scan de
    instancias, y se verifica contra el resumen del propio deck (ver `verificar_resumen`).
    `--full-walk` fuerza el recorrido exhaustivo para validar que el plan no pierde nada.
    """
    if full_walk or not prescan:
        return list(range(n_slides))
    return sorted({int(t["slide"]) for t in prescan} | {n_slides - 1})


def verificar_resumen(cierre: dict) -> dict:
    """
    Oráculo de verificación: el slide de resumen del CoursePresentation lista, actividad por
    actividad, su slide, su porcentaje y su puntaje. Eso permite comprobar que no quedó ninguna
    sin resolver sin recorrer el deck entero.
    """
    import re

    txt = (cierre or {}).get("resumen_deck") or ""
    acts = re.findall(r"Diapositiva\s+(\d+):\s*Actividad\s+(\d+)\s+(\d+)%\s+(\d+)/(\d+)", txt)
    detalle = [{"slide": int(a), "actividad": int(b), "pct": int(c),
                "score": int(d), "max": int(e)} for a, b, c, d, e in acts]
    return {"actividades_en_resumen": len(detalle),
            "todas_al_100": bool(detalle) and all(x["pct"] == 100 for x in detalle),
            "suma_score": sum(x["score"] for x in detalle),
            "suma_max": sum(x["max"] for x in detalle),
            "detalle": detalle}


def walk_deck(b: Browser, plan: list, n_slides: int, m: dict, dry_run: bool,
              use_jev_guard: bool = False) -> dict:
    """
    Recorre TODO el deck slide por slide y resuelve la tarea que aparezca en cada uno.

    Regla (Andrés, 2026-09-14): resolver el quiz NO cierra la actividad. Si el quiz está en el
    slide 5 de 12, hay que seguir hasta el 12 o el deck queda incompleto. Y no se puede asumir
    que hay UN solo quiz ni que está siempre al final: por eso se camina el deck entero y se
    pregunta en CADA slide qué tareas tiene, en vez de confiar en un pre-scan de tipos.
    """
    tareas, unknowns, nav, ultimo = [], [], 0, None
    visitados = 0
    for si in plan:
        if not goto_slide(b, si, m):
            continue                     # el salto no se confirmó: no se opera a ciegas
        visitados += 1
        _, st = b.wait_for(js(JS_SLIDE_TASKS, si=si), timeout=4,
                           until=lambda r: r and r.get("cur") == si)
        if st is None:
            m["opportunities"].append(f"slide_no_renderizo:{si}")
            st = b.ev(js(JS_SLIDE_TASKS, si=si)) or {}
        if st.get("cur") is not None:
            ultimo = st["cur"]
        nav += st.get("nav", 0)
        for u in st.get("unknown", []):
            unknowns.append(f"slide{si}:child{u.get('i')}:{u.get('cls') or 'sin-clase'}")
        for t in st.get("tasks", []):
            machine = t["machine"]
            if machine not in SOLVERS:
                m["opportunities"].append(f"tipo_no_soportado:{machine}")
                tareas.append({"type": machine, "slide": si, "unsupported": True})
                continue
            if dry_run:
                tareas.append({"type": machine, "slide": si, "dry_run": True})
                continue
            sel = TASK_SELECTOR.get(machine, ".h5p-question")
            _, rdy = b.wait_for(js(JS_TASK_READY_DOM, si=si, sel=sel), timeout=8,
                                until=lambda r: r and r.get("ok"))
            if rdy is None:
                m["opportunities"].append("slide_no_renderizo:" + machine)
            r = SOLVERS[machine](b, si, t["child"], m)
            r["slide"] = r.get("slide", si)
            # Optional JEV guardarraíl: only fires when the orchestrator requested it
            # AND the shim is reachable. The verdict is metadata — the existing
            # done-detection logic keeps working; the guard just records uncertainty.
            if use_jev_guard and _JEV_SHIM["available"]:
                try:
                    slide_state = b.ev(js(JS_SLIDE_TASKS, si=si)) or {}
                    guard = _JEV_SHIM["slide_done"](
                        json.dumps(slide_state, separators=(",", ":"), default=str)
                    )
                    if guard.get("uncertain"):
                        m["opportunities"].append(f"jev_guard_uncertain:{machine}:slide{si}")
                    elif not guard.get("confident_done"):
                        m["opportunities"].append(f"jev_guard_disagrees:{machine}:slide{si}")
                    r["jev_guard"] = {
                        "mode": guard.get("mode"),
                        "confident_done": guard.get("confident_done"),
                        "uncertain": guard.get("uncertain"),
                        "reason": guard.get("error_reason"),
                        "cost_usd": guard.get("cost_usd"),
                        "latency_ms": guard.get("latency_ms"),
                    }
                except Exception as e:
                    m["opportunities"].append(f"jev_guard_exception:{type(e).__name__}")
            tareas.append(r)
    if unknowns:
        m["opportunities"].append("nodos_no_clasificados:" + str(len(unknowns)))
    return {"tareas": tareas, "slides_visitados": visitados, "ultimo_slide": ultimo,
            "plan": list(plan), "nav_hotspots": nav, "unknown": unknowns[:5]}


def finish_deck(b: Browser, total: int, m: dict) -> dict:
    """
    Cierra el deck: ir al ÚLTIMO slide y pulsar el botón de chequeo final.

    Regla (Andrés, 2026-09-14): resolver el quiz NO cierra la actividad. El último slide es
    `.h5p-summary-slide` y su botón es "Mostrar solución" (`.h5p-show-solutions`), que activa el
    modo solución y cierra el intento. Sin ese clic el deck queda a medias (p. ej. 5/13) y la
    actividad NO está completa, aunque todos los quizzes estén al 100%.
    """
    last = total - 1
    goto_slide(b, last, m)
    _, st = b.wait_for(JS_FINAL_STATE, timeout=10, until=lambda r: r and r.get("cur") == last)
    st = st or b.ev(JS_FINAL_STATE) or {}
    clicked = b.ev(JS_CLICK_FINAL) or {}
    if not clicked.get("clicked"):
        m["opportunities"].append("boton_final_no_encontrado")
    else:
        b.wait_for(JS_FINAL_STATE, timeout=8, until=lambda r: r and r.get("isSolutionMode"))
    fin = b.ev(JS_FINAL_STATE) or {}
    if not fin.get("isSummary"):
        m["opportunities"].append("ultimo_slide_no_es_resumen")
    if clicked.get("clicked") and not fin.get("isSolutionMode"):
        m["opportunities"].append("chequeo_final_no_activo")
    return {"total_slides": total, "ultimo_slide": fin.get("cur"),
            "es_resumen": fin.get("isSummary"),
            "boton_final": clicked.get("label"),
            "modo_solucion": fin.get("isSolutionMode"),
            "resumen_deck": fin.get("resumen")}


# --- FindTheWords (sopa de letras) -------------------------------------------- #
# El tablero se dibuja en <canvas>: no hay celdas en el DOM que clickear. La única forma FIEL de
# resolverlo es enviar eventos de mouse REALES por CDP (`Input.dispatchMouseEvent`), que pasan por
# el pipeline de input del navegador y sí disparan los handlers mousedown/mousemove/mouseup de la
# librería (los eventos sintéticos de JS NO los disparan).
JS_FTW_OFFSET = r"""
(()=>{
  const f = document.querySelector('iframe.h5p-iframe');
  if (!f) return JSON.stringify({err: 'sin iframe'});
  const r = f.getBoundingClientRect();
  return JSON.stringify({x: r.x, y: r.y, innerH: window.innerHeight, innerW: window.innerWidth,
                         sy: window.scrollY, sx: window.scrollX});
})()
"""

JS_FTW_READY = r"""
(()=>{
  // El grid de FindTheWords se CONSTRUYE de forma asíncrona: la instancia H5P puede existir
  // (JS_MAP la ve) y `$drawingCanvas` todavía no. Leer la geometría antes lanza 'Uncaught'.
  const w = window[0];
  const I = w && w.H5P && w.H5P.instances && w.H5P.instances[0];
  if (!I || !I.grid || !I.grid.$drawingCanvas || !I.grid.wordGrid || !I.grid.wordGrid.length)
    return JSON.stringify({ok: false});
  return JSON.stringify({ok: true, n: I.grid.wordGrid.length});
})()
"""

JS_FTW_GEO = r"""
(()=>{
  const I = window[0].H5P.instances[0], g = I.grid;
  const r = g.$drawingCanvas[0].getBoundingClientRect();
  return JSON.stringify({rows: g.wordGrid.length, cols: g.wordGrid[0].length, es: g.elementSize,
    canvas: {x: r.x, y: r.y, w: r.width, h: r.height},
    words: I.vocabulary.words, grid: g.wordGrid.map(x => x.join(''))});
})()
"""

JS_FTW_STATE = r"""
(()=>{
  const I = window[0].H5P.instances[0];
  return JSON.stringify({numFound: I.numFound, max: I.getMaxScore(), score: I.getScore(),
    found: I.vocabulary.wordsFound.slice(0, 40), gameStarted: I.isGameStarted});
})()
"""

JS_FTW_MARK = r"""
(()=>{
  // FALLBACK (último recurso, tras 2 drags fallidos): reproducir EXACTAMENTE lo que hace el
  // handler `drawEnd` de la librería cuando el usuario encuentra una palabra:
  //   vocabulary.checkWord(word) -> numFound++ -> counter.increment() -> grid.markWord(wordObject)
  // Se usa solo cuando el drag real no registra la palabra (p. ej. el extremo cae fuera del
  // viewport y el evento no llega). Queda marcado como `via: api` en el resultado, sin ocultarlo.
  const I = window[0].H5P.instances[0];
  const p = __PARAMS__;
  if (I.vocabulary.wordsFound.indexOf(p.word) !== -1) return JSON.stringify({ok: true, ya: true});
  if (!I.vocabulary.checkWord(p.word)) return JSON.stringify({ok: false, why: 'checkWord rechazo'});
  I.numFound++;
  try { if (I.counter && I.counter.increment) I.counter.increment(); } catch (e) {}
  try {
    I.grid.markWord({directionKey: p.dirKey, start: {x: p.x0, y: p.y0}, end: {x: p.x1, y: p.y1}});
  } catch (e) {}
  return JSON.stringify({ok: true, numFound: I.numFound});
})()
"""

JS_FTW_SUBMIT = r"""
(()=>{
  const d = window[0].document;
  const b = Array.from(d.querySelectorAll('button, .h5p-joubelui-button'))
                 .filter(x => x.getClientRects().length > 0)
                 .find(x => /check|comprobar|enviar|submit/i.test(x.textContent || ''));
  if (!b) return JSON.stringify({clicked: false});
  b.click();
  return JSON.stringify({clicked: true, label: (b.textContent || '').trim().slice(0, 30)});
})()
"""

_FTW_DIRS = {"E": (1, 0), "W": (-1, 0), "S": (0, 1), "N": (0, -1),
             "SE": (1, 1), "SW": (-1, 1), "NE": (1, -1), "NW": (-1, -1)}


def _ajustar_viewport(b, cvs: dict, m: dict) -> dict:
    """
    Zoom out vía `Emulation.setDeviceMetricsOverride` para que el TABLERO COMPLETO entre en el
    viewport, sin scroll.

    Idea de Andrés (2026-09-14): en vez de scrollear palabra por palabra (frágil: el rect se mueve
    al marcarse palabras, y hay que acertar en los dos ejes), se agranda el viewport lógico y
    todas las celdas quedan dentro => los drags son triviales y se ahorran los round-trips de
    scroll. Se limpia al terminar porque la pestaña se REUSA (dejar la emulación puesta
    contaminaría la próxima corrida).
    """
    off = b.ev(JS_FTW_OFFSET) or {}
    ancho = int(off.get("x", 0) + cvs["x"] + cvs["w"] + 40)
    alto = int(off.get("y", 0) + cvs["y"] + cvs["h"] + 40)
    b._cmd("Emulation.setDeviceMetricsOverride",
           {"width": max(ancho, 900), "height": max(alto, 700),
            "deviceScaleFactor": 1, "mobile": False})
    return {"viewport": [max(ancho, 900), max(alto, 700)]}


def _hallar_palabra(word: str, grid: list, rows: int, cols: int):
    """Ubica la palabra en la matriz de letras: devuelve (x, y, dir, dx, dy) o None."""
    w = word.replace(" ", "").upper()
    for y in range(rows):
        for x in range(cols):
            for d, (dx, dy) in _FTW_DIRS.items():
                if all(0 <= x + dx * k < cols and 0 <= y + dy * k < rows
                       and grid[y + dy * k][x + dx * k].upper() == ch
                       for k, ch in enumerate(w)):
                    return x, y, d, dx, dy
    return None


def _drag_ftw(b, cvs: dict, es: int, x0: int, y0: int, x1: int, y1: int, pasos: int = 6,
              m: dict | None = None, use_jev_guard: bool | None = None) -> None:
    """
    Arrastra de la celda (x0,y0) a (x1,y1) con eventos de mouse reales.

    Tres trampas ya pagadas: (a) CDP usa coordenadas del viewport SUPERIOR, hay que sumar el rect
    del iframe porque dentro del iframe getBoundingClientRect() es relativo al iframe; (b) si la
    celda queda fuera del viewport (palabras verticales largas) el evento no llega, así que se
    scrollea para centrar la palabra y se recalcula el offset; (c) hay que emitir AL MENOS un
    `mouseMoved` por celda: con pasos fijos el puntero salta celdas intermedias y la librería
    reconstruye una palabra más corta (PUNTODEREORDEN, 15 letras, fallaba con 6 pasos).
    """
    if use_jev_guard is None:
        use_jev_guard = _USE_JEV_GUARD

    # Guardarraíl de drag (escenario 2). Corre UNA vez por drag. Nunca bloquea:
    # en fallback/error el veredicto es `uncertain` y el cálculo de viewport de
    # abajo corre igual. Solo registra la decisión en `opportunities`.
    if use_jev_guard and m is not None:
        try:
            off0 = b.ev(JS_FTW_OFFSET) or {}
            geo0 = {
                "canvas": cvs,
                "start_xy": [x0 * es + es / 2, y0 * es + es / 2],
                "end_xy": [x1 * es + es / 2, y1 * es + es / 2],
                "viewport_inner": [off0.get("innerW"), off0.get("innerH")],
                "iframe_offset": [off0.get("x"), off0.get("y")],
                "element_size": es,
            }
            guard = _JEV_SHIM["drag_safe"](geo0)
            if guard.uncertain:
                m["opportunities"].append("jev_drag_uncertain")
            elif guard.decision == "fail":
                m["opportunities"].append("jev_drag_disagrees")
        except Exception as e:
            m["opportunities"].append(f"jev_drag_exception:{type(e).__name__}")

    for intento in range(2):
        off = b.ev(JS_FTW_OFFSET) or {}
        oy, ox = off.get("y", 0), off.get("x", 0)
        inner_h = off.get("innerH", 1000)
        inner_w = off.get("innerW", 1400)
        py0 = oy + cvs["y"] + y0 * es + es / 2
        py1 = oy + cvs["y"] + y1 * es + es / 2
        px0 = ox + cvs["x"] + x0 * es + es / 2
        px1 = ox + cvs["x"] + x1 * es + es / 2
        # Vertical Y HORIZONTAL: si un extremo cae fuera del viewport el evento no llega.
        # Faltaba el eje X: con el canvas a la derecha (x≈1098 sobre un viewport de ~1105) las
        # palabras largas empezaron a fallar (PUNTODEREORDEren) y palabras cortas como EOQ
        # se quedaban sin marcar.
        lo_y, hi_y = sorted([py0, py1])
        lo_x, hi_x = sorted([px0, px1])
        necesita_y = hi_y > inner_h - 30 or lo_y < 30
        necesita_x = hi_x > inner_w - 30 or lo_x < 30
        if necesita_y or necesita_x:
            dest_y = max(0, (lo_y + hi_y) / 2 - inner_h / 2) if necesita_y else off.get("sy", 0)
            dest_x = max(0, (lo_x + hi_x) / 2 - inner_w / 2) if necesita_x else off.get("sx", 0)
            b.ev(f"(()=>{{window.scrollTo({dest_x},{dest_y});"
                 "return JSON.stringify({sy:window.scrollY})})()")
            time.sleep(0.45)
            off = b.ev(JS_FTW_OFFSET) or {}
            oy, ox = off.get("y", 0), off.get("x", 0)
        sx = ox + cvs["x"] + x0 * es + es / 2
        sy = oy + cvs["y"] + y0 * es + es / 2
        ex = ox + cvs["x"] + x1 * es + es / 2
        ey = oy + cvs["y"] + y1 * es + es / 2
        b._cmd("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": round(sx), "y": round(sy), "buttons": 0})
        b._cmd("Input.dispatchMouseEvent", {"type": "mousePressed", "x": round(sx), "y": round(sy),
                                            "button": "left", "clickCount": 1, "buttons": 1})
        for i in range(1, pasos + 1):
            t = i / float(pasos)
            b._cmd("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": round(sx + (ex - sx) * t),
                                                "y": round(sy + (ey - sy) * t),
                                                "button": "left", "buttons": 1})
            time.sleep(0.03)
        b._cmd("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": round(ex), "y": round(ey),
                                            "button": "left", "clickCount": 1, "buttons": 0})
        time.sleep(0.45)
        if intento == 0:
            return           # el llamador decide si reintentar seg\u00fan el estado


_FTW_DIRKEY = {"E": "horizontal", "W": "horizontal",
               "S": "vertical", "N": "vertical",
               "SE": "diagonal", "NW": "diagonalUpBack",
               "SW": "diagonalBack", "NE": "diagonalUp"}


def solve_findthewords(b, si, ci, m: dict) -> dict:
    """H5P.FindTheWords: sopa de letras resuelta con drags reales de CDP."""
    if not isinstance(b, ChromeBrowser):
        m["opportunities"].append("findthewords_requiere_chrome_cdp")
        return {"type": "H5P.FindTheWords", "unsupported": True,
                "why": "los drags sintéticos de JS no disparan los handlers; hace falta CDP"}
    b.wait_for(JS_FTW_READY, timeout=20, until=lambda r: r and r.get("ok"))
    geo = b.ev(JS_FTW_GEO) or {}
    if not geo.get("words"):
        m["opportunities"].append("ftw_sin_geometria")
        return {"type": "H5P.FindTheWords", "unsupported": True}
    grid, es, cvs = geo["grid"], geo["es"], geo["canvas"]
    rows, cols = geo["rows"], geo["cols"]
    # ZOOM OUT: que el tablero completo entre sin scroll (y releer geometría tras el relayout).
    zoom = None
    try:
        zoom = _ajustar_viewport(b, cvs, m)
        time.sleep(0.4)
        geo2 = b.ev(JS_FTW_GEO) or {}
        if geo2.get("canvas"):
            cvs, es = geo2["canvas"], geo2.get("es", es)
    except Exception:
        m["opportunities"].append("ftw_zoom_no_aplicado")

    st = b.ev(JS_FTW_STATE) or {}
    if st.get("max") and st.get("numFound") == st.get("max"):
        m["skipped_tasks"] += 1
        return {"type": "H5P.FindTheWords", "score": st.get("numFound"), "max": st.get("max"),
                "note": "ya resuelto"}

    fallos = []
    for w in geo["words"]:
        st = b.ev(JS_FTW_STATE) or {}
        if w in (st.get("found") or []):
            continue
        pos = _hallar_palabra(w, grid, rows, cols)
        if not pos:
            fallos.append({"palabra": w, "motivo": "no está en la matriz"})
            continue
        x0, y0, dirn, dx, dy = pos
        n = len(w.replace(" ", ""))
        for intento in (1, 2):
            # GEOMETRÍA FRESCA por palabra: al marcar una palabra cambia la lista de vocabulario y
            # con ella la altura de la página, así que el rect del canvas se mueve. Usar el rect
            # leído una sola vez al inicio hacía fallar las últimas palabras (7/9 en 774617).
            g2 = b.ev(JS_FTW_GEO) or {}
            _drag_ftw(b, g2.get("canvas") or cvs, g2.get("es") or es,
                      x0, y0, x0 + dx * (n - 1), y0 + dy * (n - 1),
                      pasos=max(n, 6), m=m, use_jev_guard=_USE_JEV_GUARD)
            m["clicks"] += 1
            st = b.ev(JS_FTW_STATE) or {}
            if w in (st.get("found") or []):
                via_drag = True
                break
        else:
            # Drag agotado: último recurso por API interna (mismo efecto sobre el estado).
            params = {"word": w, "dirKey": _FTW_DIRKEY.get(dirn, "horizontal"),
                      "x0": x0, "y0": y0, "x1": x0 + dx * (n - 1), "y1": y0 + dy * (n - 1)}
            fb = b.ev(js(JS_FTW_MARK, PARAMS=json.dumps(params))) or {}
            st = b.ev(JS_FTW_STATE) or {}
            if fb.get("ok") and w in (st.get("found") or []):
                marca = {"palabra": w, "via": "api", "motivo": "el drag no la registró"}
                fallos.append(marca)
                m["opportunities"].append("ftw_resuelto_por_api_no_por_drag")
            else:
                fallos.append({"palabra": w, "via": "api", "motivo": "ni el drag ni la API"})

    st = b.ev(JS_FTW_STATE) or {}
    score, mx = st.get("numFound"), st.get("max")
    # Limpiar el viewport emulado: la pestaña se reusa y la emulación no debe persistir.
    if zoom:
        try:
            b._cmd("Emulation.clearDeviceMetricsOverride")
        except Exception:
            pass
    if mx and score != mx:
        m["opportunities"].append(f"ftw_palabras_faltantes:{len(fallos)}")
    sub = b.ev(JS_FTW_SUBMIT) or {}
    return {"type": "H5P.FindTheWords", "score": score, "max": mx,
            "palabras": len(geo["words"]), "fallos": fallos, "submit": sub,
            "zoom": zoom}


SOLVERS = {
    "H5P.Blanks": solve_blanks,
    "H5P.SingleChoiceSet": solve_scs,
    "H5P.MultiChoice": solve_question,
    "H5P.TrueFalse": solve_question,
    "H5P.MarkTheWords": solve_question,
    "H5P.DragQuestion": solve_dragq,
    "H5P.FindTheWords": solve_findthewords,
}


def solve_activity(b: Browser, hvp_id: str, m: dict, dry_run: bool) -> dict:
    t0 = time.time()
    b.goto(f"{BASE}/mod/hvp/view.php?id={hvp_id}")
    _, ready = b.wait_for(JS_MAP, timeout=20, until=lambda r: r and r.get("ready"))
    if not ready or not ready.get("ready"):
        pre = b.ev(JS_PREFLIGHT) or {}
        if pre.get("visibility") == "hidden" or pre.get("readyState") not in ("complete", "interactive"):
            # Causa real vista en vivo (2026-09-14): 5 superficies abiertas como TABS del mismo
            # pane compartían un solo slot visible; la que perdía el foco se suspendía y su
            # `goto` quedaba a medias. Diagnosticarlo como "h5p_no_cargo" mandaba a buscar el
            # problema en el contenido, que estaba perfecto.
            m["opportunities"].append("surface_throttled_segundo_plano")
        else:
            m["opportunities"].append("h5p_no_cargo")
        return {"hvp": hvp_id, "error": "H5P no cargó", "preflight": pre, "ok": False}

    inst = ready["instances"][0]
    rec = {"hvp": hvp_id, "lib": inst["lib"], "contentId": inst["contentId"],
           "tasks": [], "score": inst.get("score"), "max": inst.get("max")}

    n_slides = inst.get("slides") or 0
    prescan = [t for t in inst.get("tasks", []) if t["machine"] not in CONTAINERS]
    full_walk = bool(m.get("full_walk"))
    plan = plan_deck(n_slides, prescan, full_walk)
    if n_slides:
        walk = walk_deck(b, plan, n_slides, m, dry_run,
                         use_jev_guard=use_jev_guard)
    else:
        # Contenido que no es un contenedor: una sola tarea suelta.
        walk = {"tareas": [], "slides_visitados": 0, "ultimo_slide": None, "plan": [],
                "nav_hotspots": 0, "unknown": []}
        machine = inst.get("machine")
        if machine not in SOLVERS:
            m["opportunities"].append(f"tipo_no_soportado:{machine}")
            walk["tareas"].append({"type": machine, "unsupported": True})
        elif not dry_run:
            walk["tareas"].append(SOLVERS[machine](b, 0, 0, m))

    rec["tasks"] = walk["tareas"]
    rec["slides"] = {"total": n_slides, "visitados": walk["slides_visitados"],
                     "plan": walk.get("plan"), "ultimo": walk["ultimo_slide"],
                     "nav_hotspots": walk["nav_hotspots"], "full_walk": full_walk}
    rec["nodos_no_clasificados"] = walk["unknown"]
    # El pre-scan no debe perder nada: si difiere del walk, es un bug de detección, no del contenido.
    # Normalizar el prefijo: el pre-scan da slugs (`H5P.Blanks`) y los solvers devuelven el nombre
    # corto (`Blanks`). Compararlos crudos produce un falso positivo permanente.
    preset = {(t["slide"], str(t["machine"]).replace("H5P.", "")) for t in prescan}
    walkset = {(t.get("slide"), str(t.get("type")).replace("H5P.", "")) for t in walk["tareas"]}
    if n_slides and preset != walkset:
        m["opportunities"].append(f"prescan_no_coincide_con_walk:pre={sorted(preset)}|walk={sorted(walkset)}")
    # Cerrar exige DOS cosas cuando ES un deck: recorrerlo hasta el final Y pulsar el chequeo
    # final del resumen. Resolver las tareas no alcanza. Si NO es un deck (p. ej. H5P.FindTheWords,
    # que no tiene slides), no hay deck que completar: exigirlo daba un falso negativo (774623 se
    # resolvió 9/9 y se reportó como incompleto).
    if n_slides and not dry_run:
        rec["cierre"] = finish_deck(b, n_slides, m)
    cierre = rec.get("cierre") or {}
    if not n_slides:
        rec["deck_completo"] = True
    elif dry_run:
        rec["deck_completo"] = None
    else:
        rec["deck_completo"] = (cierre.get("ultimo_slide") == n_slides - 1
                                and bool(cierre.get("es_resumen"))
                                and bool(cierre.get("modo_solucion")))
    if n_slides and not rec["deck_completo"]:
        m["opportunities"].append("deck_incompleto")

    # --- Oráculo de verificación: el propio resumen del deck ---
    # El slide de resumen lista actividad por actividad su slide, su % y su puntaje. Eso permite
    # comprobar que el PLAN no se comió ninguna actividad sin recorrer los 13 slides.
    ver = verificar_resumen(rec.get("cierre"))
    rec["verificacion_resumen"] = ver
    if (n_slides and not dry_run and ver["actividades_en_resumen"] > len([t for t in walk["tareas"] if t.get("max")])):
        # El resumen conoce más actividades de las que el plan cubrió => el atajo perdió algo.
        # Se cae a recorrido completo UNA vez (nunca en bucle) y se vuelve a cerrar el deck.
        m["opportunities"].append("plan_incompleto_fallback_full_walk")
        walk = walk_deck(b, list(range(n_slides)), n_slides, m, dry_run,
                         use_jev_guard=use_jev_guard)
        rec["tasks"] = walk["tareas"]
        rec["slides"]["visitados"] = walk["slides_visitados"]
        rec["slides"]["plan"] = walk.get("plan")
        rec["cierre"] = finish_deck(b, n_slides, m)
        ver = verificar_resumen(rec.get("cierre"))
        rec["verificacion_resumen"] = ver

    _, cur = b.wait_for(JS_MAP, timeout=8, until=lambda r: r and r.get("ready"))
    if cur and cur.get("instances"):
        rec["score"] = cur["instances"][0].get("score")
        rec["max"] = cur["instances"][0].get("max")

    if not dry_run:
        rec["finish"] = b.ev(JS_FINISH) or {}
        took, posted = b.wait_for(JS_XAPI_POSTED, timeout=8,
                                  until=lambda r: r and r.get("hits", 0) > 0)
        rec["xapi_posted"] = (posted or {}).get("hits", 0)
        if took is None:
            m["opportunities"].append("xapi_no_confirmado")

    rec["elapsed_s"] = round(time.time() - t0, 1)
    if dry_run:
        rec["ok"] = None              # en dry-run no hay veredicto: no es una oportunidad
        return rec
    if not rec.get("max"):
        m["opportunities"].append(f"sin_tareas_puntuables:{hvp_id}")
        rec["ok"] = False
    else:
        # ok exige: score al máximo + deck recorrido hasta el resumen + chequeo final pulsado
        # + (si el resumen lista actividades) que TODAS figuren al 100%.
        ver = rec.get("verificacion_resumen") or {}
        rec["ok"] = (rec.get("score") == rec.get("max")
                     and bool(rec.get("deck_completo"))
                     and (ver.get("todas_al_100") if ver.get("actividades_en_resumen") else True))
    if rec["ok"]:
        m["solved"] += 1
    elif rec.get("max") and rec.get("score") != rec.get("max"):
        m["opportunities"].append(f"score_incompleto:{hvp_id}")
    elif not rec.get("deck_completo"):
        m["opportunities"].append(f"deck_incompleto:{hvp_id}")
    return rec


# --------------------------------------------------------------------------- #
# Reporte de oportunidades (ritual de mejora continua)                          #
# --------------------------------------------------------------------------- #
def report(course_id: str, dest: Path | None) -> None:
    from collections import Counter

    led = load_ledger(ledger_path(course_id, dest))
    acts = led.get("activities", {})
    print(f"Ledger {course_id}: {len(acts)} contenidos, actualizado {led.get('updated')}")
    for hvp, a in sorted(acts.items()):
        flag = "OK  " if a.get("ok") else "PEND"
        sl = a.get("slides") or {}
        ver = a.get("verificacion_resumen") or {}
        cierre = a.get("cierre") or {}
        plan = len(sl.get("plan") or [])
        total = sl.get("total") or 1
        deck = f"deck {sl.get('ultimo')}/{total - 1}"
        atajo = f"plan {plan}/{total}"
        check = "final✓" if cierre.get("modo_solucion") else "final✗"
        resumen = (f"resumen {ver.get('actividades_en_resumen', 0)}act "
                   f"{'100%' if ver.get('todas_al_100') else 'INCOMPLETO'}")
        print(f"  [{flag}] {hvp} {str(a.get('lib','?')):24} {a.get('score')}/{a.get('max')} "
              f"{deck} {atajo} {check} {resumen} {a.get('elapsed_s','?')}s")
    if not LESSONS.exists():
        print("\nSin log de lecciones todavía.")
        return
    rows = [json.loads(x) for x in LESSONS.read_text(encoding="utf-8").splitlines() if x.strip()]
    c, skips, secs = Counter(), 0, 0.0
    for r in rows:
        for o in r.get("opportunities", []):
            c[o.split(":")[0]] += 1
        skips += r.get("skipped_idempotent", 0)
        secs += r.get("elapsed_s", 0)
    print(f"\nLecciones acumuladas: {len(rows)} runs · {skips} tareas saltadas por "
          f"idempotencia · {secs:.0f}s totales")
    if c:
        print("Oportunidades por frecuencia:")
        for k, v in c.most_common():
            print(f"  {v:3}×  {k}")
        top = c.most_common(1)[0][0]
        print(f"\nSiguiente optimización → atacar `{top}` (apareció {c[top]}×). "
              f"Si es recurrente, se automatiza en h5p_solve.py en vez de resolverse a mano.")
    else:
        print("Sin oportunidades pendientes: el solver cubrió todo sin fricción.")


def log_lessons(course_id: str, m: dict, results: list[dict]) -> None:
    LESSONS.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "course": course_id,
        "activities": len(results),
        "solved": m["solved"],
        "browser_calls": m["calls"],
        "clicks": m["clicks"],
        "skipped_idempotent": m["skipped"] + m["skipped_tasks"],
        "elapsed_s": round(m["elapsed"], 1),
        "opportunities": sorted(set(m["opportunities"])),
        "dest": str(m.get("dest") or Path.cwd()),
    }
    with LESSONS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Solver idempotente de H5P en Moodle Uniremington")
    ap.add_argument("--course-id", required=True)
    ap.add_argument("--surface", default="surface:9")
    ap.add_argument("--backend", choices=["cmux", "chrome"], default="cmux",
                    help="cmux = WKWebView (una superficie por pane); chrome = CDP (N pestañas, sin foco)")
    ap.add_argument("--cdp-port", type=int, default=9224,
                    help="puerto CDP de Chrome (9224 = perfil autorizado de Moodle)")
    ap.add_argument("--cdp-tab", default=None, help="targetId de una pestaña ya abierta")
    ap.add_argument("--dest", type=Path, default=None, help="raíz del curso (para _cache/)")
    ap.add_argument("--only", default="", help="ids HVP separados por coma")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--full-walk", action="store_true",
                    help="recorrer TODOS los slides en vez del plan (actividades + resumen). "
                         "Usar para validar que el atajo no pierde nada.")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--keep-tab", action="store_true",
                    help="no cerrar la pestaña al terminar (por defecto SÍ se cierra: sin esto cada corrida deja una huérfana)")
    ap.add_argument("--cleanup-tabs", action="store_true",
                    help="cerrar las pestañas huérfanas del Aula Virtual que dejaron corridas anteriores y salir")
    ap.add_argument("--keep-tabs-n", type=int, default=0,
                    help="con --cleanup-tabs: cuántas dejar vivas (default 0)")
    ap.add_argument("--tab-policy", choices=["reuse", "new"], default="reuse",
                    help="reuse (default) = adoptar una pestaña existente del Aula Virtual; "
                         "new = abrir la propia (OBLIGATORIO en fan-out paralelo, si no los agentes se pisan la pestaña)")
    ap.add_argument("--force", action="store_true", help="re-resolver aunque el ledger diga OK")
    args = ap.parse_args()

    global _USE_JEV_GUARD
    _USE_JEV_GUARD = bool(args.use_jev_guard)

    if args.cleanup_tabs:
        print(json.dumps(cerrar_pestanas_huerfanas(args.cdp_port, args.keep_tabs_n),
                         ensure_ascii=False, indent=1))
        return 0

    if args.report:
        report(args.course_id, args.dest)
        return 0

    b = (ChromeBrowser(args.cdp_port, url=None, target_id=args.cdp_tab,
                       reuse=(args.tab_policy == "reuse"))
         if args.backend == "chrome" else Browser(args.surface))
    b._keep_tab = args.keep_tab or (args.tab_policy == "reuse")
    _STATE["cdp_port"] = args.cdp_port
    _STATE["tab_policy"] = args.tab_policy
    _BROWSERS.append(b)          # el finally global cierra la pestaña: nada de huérfanas
    t0 = time.time()
    m = {"clicks": 0, "solved": 0, "skipped": 0, "skipped_tasks": 0, "calls": 0,
         "opportunities": [], "elapsed": 0.0, "dest": args.dest,
         "full_walk": args.full_walk}

    led_p = ledger_path(args.course_id, args.dest)
    led = load_ledger(led_p)
    led["course"] = args.course_id

    # --- Descubrimiento AUTORITATIVO: el informe de calificaciones ---
    def leer_informe():
        b.goto(f"{BASE}/grade/report/user/index.php?id={args.course_id}")
        _, it = b.wait_for(JS_GRADE_H5P, timeout=25, until=lambda r: r and len(r))
        return it or []

    def al_cien(it):
        return "100,00" in (it.get("pct") or "")

    items = leer_informe()
    if not items:
        print("ERROR: el informe de calificaciones no devolvió contenidos interactivos")
        return 2

    if args.only:
        want = {x.strip() for x in args.only.split(",")}
        objetivo = [i for i in items if i["id"] in want]
    else:
        objetivo = [i for i in items if not al_cien(i)]

    n_ok = len([i for i in items if al_cien(i)])
    print(f"Informe: {len(items)} contenidos interactivos · {n_ok} al 100% · "
          f"{len(objetivo)} en objetivo")
    for i in items:
        print(f"  [{'OK  ' if al_cien(i) else 'PEND'}] {i['id']} {i['nombre'][:54]:54} "
              f"{i['calificacion'] or '-':>6} {i['pct'] or '-':>9}")

    results = []
    for i in objetivo:
        hvp_id = i["id"]
        if al_cien(i) and not args.force:
            m["skipped"] += 1
            print(f"  = {hvp_id} ya está al 100% en el informe — se salta")
            continue
        print(f"  → {hvp_id} {i['nombre'][:60]}")
        rec = solve_activity(b, hvp_id, m, args.dry_run)
        rec["name"] = i["nombre"]
        rec["informe_antes"] = i
        results.append(rec)
        led["activities"][hvp_id] = rec
        if not args.dry_run:
            save_ledger(led_p, led)    # checkpoint por actividad: un fallo no pierde lo hecho
        print(f"     score={rec.get('score')}/{rec.get('max')} ok={rec.get('ok')} "
              f"deck={rec.get('deck_completo')} xapi={rec.get('xapi_posted')}")

    # --- Verificación FINAL contra el mismo informe (fuente autoritativa) ---
    if not args.dry_run and objetivo:
        b.goto(f"{BASE}/course/view.php?id={args.course_id}")
        b.wait_for(JS_COURSE_H5P, timeout=20, until=lambda r: r)
        for i in objetivo:
            r = b.ev(js(JS_MARK_DONE, id=i["id"])) or {}
            if r.get("clicked"):
                print(f"  ✓ finalización marcada: {i['id']}")
                time.sleep(0.4)
        final = {x["id"]: x for x in leer_informe()}
        fallan = [i["id"] for i in objetivo if not al_cien(final.get(i["id"], {}))]
        print(f"\nVERIFICACIÓN en el informe: {len(objetivo) - len(fallan)}/{len(objetivo)} al 100%")
        for pid in fallan:
            f = final.get(pid, {})
            print(f"  ✗ {pid} {str(f.get('nombre'))[:48]} → {f.get('calificacion') or '-'} "
                  f"({f.get('pct') or '-'})")
            m["opportunities"].append(f"informe_no_al_100:{pid}")
        if not fallan:
            print("  ✓ todo el objetivo quedó en 10,00 (100%)")

    m["calls"] = b.calls
    m["elapsed"] = time.time() - t0
    log_lessons(args.course_id, m, results)

    print(f"\nResumen: {m['solved']} resueltos · {m['skipped']} ya estaban · "
          f"{m['clicks']} clics · {m['elapsed']:.0f}s · {b.calls} llamadas al navegador")
    if m["opportunities"]:
        print("Oportunidades detectadas:")
        for o in sorted(set(m["opportunities"])):
            print(f"  · {o}")
        print(f"→ Revisar: h5p_solve.py --course-id {args.course_id} --report")
    return 0


if __name__ == "__main__":
    codigo = 3
    try:
        codigo = main()
    except SystemExit as se:
        codigo = se.code if isinstance(se.code, int) else 3
    except Exception as exc:  # noqa: BLE001 — último recurso, se registra antes de morir
        # Un fallo fatal abortaba el run SIN dejar rastro en el log de lecciones, así que la
        # oportunidad nunca se automatizaba y el mismo error volvía a costar tiempo. Registrarlo
        # antes de morir es el punto entero del ritual de mejora continua.
        cid = "desconocido"
        if "--course-id" in sys.argv:
            try:
                cid = sys.argv[sys.argv.index("--course-id") + 1]
            except IndexError:
                pass
        try:
            log_lessons(cid, {"solved": 0, "calls": 0, "clicks": 0, "skipped": 0,
                              "skipped_tasks": 0, "elapsed": 0.0, "dest": None,
                              "opportunities": [f"fatal:{type(exc).__name__}:{str(exc)[:140]}"]}, [])
        except Exception:
            pass
        print(f"FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
    finally:
        # Cerrar SIEMPRE lo que abrimos, incluso si el run murió a la mitad. Con política `reuse`
        # la pestaña adoptada NO se cierra (sirve para la próxima corrida).
        for _b in _BROWSERS:
            try:
                _b.close()
            except Exception:
                pass
        # "cierra las que sobren": con política `reuse` se deja UNA pestaña viva (la reutilizable);
        # con `new` (fan-out) no se deja ninguna.
        try:
            conservar = 1 if _STATE.get("tab_policy") == "reuse" else 0
            cerrar_pestanas_huerfanas(_STATE.get("cdp_port", 9224), conservar=conservar)
        except Exception:
            pass
    sys.exit(codigo)
