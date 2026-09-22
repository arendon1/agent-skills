#!/usr/bin/env python3
"""
slide_guardrail_demo.py — EJEMPLO APLICADO que SÍ funciona con Laya.

Los escenarios 1 y 2 del plan de decisión: un guardarraíl que confirma, antes de
declarar un slide resuelto, que de verdad alcanzó su puntaje máximo.

POR QUÉ ESTE EJEMPLO Y NO UN "AI DETECTOR"
Laya (base ModernBERT, entrenada con RCLD sobre tareas de decisión) es un motor
de VERIFICACIÓN DE ESTADO y CLASIFICACIÓN. Brilla cuando el estado es una
descripción factual y la pregunta es una propiedad concreta y comprobable —
que es exactamente el caso de "¿este slide llegó al máximo?".

Medición real que motivó esta elección (2026-09-21):
  - Verificación de estado:  slide completo 0.81 | parcial 0.13   -> discrimina
  - Juicio estilístico:      slop 0.19 | humano 0.87              -> INVERTIDO

Uso:
    python scripts/laya_on_demand.py --python <venv-con-laya> run -- \
        python examples/slide_guardrail_demo.py

    python examples/slide_guardrail_demo.py --backend openrouter   # comparar
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "scripts"))

from jev_client import JEV  # noqa: E402
from jev_schemas import SLIDE_DONE_V1, decide  # noqa: E402

# --------------------------------------------------------------------------- #
# Estados reales de slides H5P — el mismo texto que el solver puede serializar
# --------------------------------------------------------------------------- #
CASES = [
    ("SingleChoiceSet · completo", "pass",
     "H5P CoursePresentation slide 4 of 12. Task H5P.SingleChoiceSet with 3 "
     "alternatives. All three alternatives carry the answered marker, the "
     "correct one is highlighted. Internal score reports 3 of 3. currentIndex "
     "has advanced past the last question. The continuar button is visible. "
     "No input elements are pending."),

    ("SingleChoiceSet · a medias", "fail",
     "H5P CoursePresentation slide 5 of 12. Task H5P.SingleChoiceSet with 3 "
     "alternatives. Only 1 of the 3 alternatives carries the answered marker. "
     "Internal score reports 1 of 3. currentIndex is still 1. Two questions "
     "remain unanswered."),

    ("Blanks · completo", "pass",
     "H5P CoursePresentation slide 7 of 12. Task H5P.Blanks with 4 text inputs. "
     "All four inputs contain text. The check button was pressed and the "
     "feedback panel reports 4 of 4 correct. Every question has been answered "
     "and the slide is complete. Score is 4 of 4, the maximum."),

    ("Blanks · incompleto", "fail",
     "H5P CoursePresentation slide 8 of 12. Task H5P.Blanks with 4 text inputs. "
     "Two of the four inputs contain text; the other two are empty placeholders. "
     "The check button has not been pressed. Score reports 2 of 4."),

    ("DragQuestion · completo", "pass",
     "H5P CoursePresentation slide 9 of 12. Task H5P.DragQuestion with 5 "
     "draggables. Every draggable is positioned inside a drop zone. No draggable "
     "remains in the source tray. Score reports 5 of 5, maximum reached."),

    ("DragQuestion · parcial", "fail",
     "H5P CoursePresentation slide 10 of 12. Task H5P.DragQuestion with 5 "
     "draggables. Three are positioned inside drop zones; two remain in the "
     "source tray. Score reports 3 of 5."),

    ("Estado ambiguo (post-recarga)", "?",
     "H5P CoursePresentation slide 6 of 12. Task H5P.SingleChoiceSet. The deck "
     "was reloaded mid-run. Alternatives show no answered marker. Internal "
     "score reports 0 of 3, but userResponses still holds previous answers. "
     "It is unclear whether the attempt is recorded."),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Guardarraíl de slides H5P con la capa de decisión.")
    ap.add_argument("--backend", default=None, help="laya | openrouter | vercel | typesafe")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    client = JEV(backend=args.backend)
    if not args.json:
        print(f"# guardarraíl de slides · backend={client.mode} · modelo={client.model}")
        if client.mode == "fallback":
            print("# AVISO: mode=fallback — los números son un stub, no una medición.")
        print()

    rows = []
    for name, expected, state in CASES:
        v = client.classify(state, SLIDE_DONE_V1)
        a = v.as_dict()["answers"]
        d = decide("slide_done_v1", a, v.mode,
                   threshold=None if v.mode == "fallback" else _th(client.mode))
        rows.append({"name": name, "expected": expected, "decision": d["decision"],
                     "confident": d["confident"], "threshold": d["threshold"],
                     "reasons": d["reasons"], "answers": a,
                     "latency_ms": v.latency_ms, "cost_usd": v.cost_usd})

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0

    print(f"{'caso':<30} {'esperado':>9} {'decidido':>10} {'thr':>5} "
          f"{'max':>6} {'committed':>10}")
    print("-" * 78)
    ok = 0
    for r in rows:
        sa = r["answers"].get("score_at_max", {}).get("value", 0)
        aa = r["answers"].get("all_answers_committed", {}).get("value", 0)
        hit = "✓" if r["expected"] == r["decision"] else ("~" if r["decision"] == "uncertain" else "✗")
        if r["expected"] == r["decision"]:
            ok += 1
        thr = f"{r['threshold']:.2f}" if r["threshold"] is not None else "—"
        print(f"{r['name']:<30} {r['expected']:>9} {r['decision']:>9}{hit} "
              f"{thr:>5} {sa:>6.3f} {aa:>10.3f}")

    print(f"\naciertos: {ok}/{len(rows)}")
    total = sum(r["cost_usd"] for r in rows)
    lat = sum(r["latency_ms"] for r in rows)
    print(f"costo: ${total:.6f}  ·  latencia total {lat}ms  ·  "
          f"media {lat//len(rows)}ms  ·  backend={client.mode}")
    if any(r["decision"] == "fail" and r["reasons"] for r in rows):
        print("\nrazones de rechazo:")
        for r in rows:
            if r["decision"] == "fail" and r["reasons"]:
                print(f"  {r['name']:<30} {'+'.join(r['reasons'])}")
    return 0


def _th(mode: str) -> float | None:
    """Umbral del backend, leído de la config (misma fuente que el CLI)."""
    try:
        from jev_cli import threshold_for  # noqa: PLC0415
        return threshold_for(mode)
    except Exception:  # noqa: BLE001
        return {"laya": 0.40, "openrouter": 0.75}.get(mode, 0.95)


if __name__ == "__main__":
    sys.exit(main())