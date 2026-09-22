#!/usr/bin/env python3
"""
ai_check_demo.py — EJEMPLO APLICADO: scoring de "AI tells" con Laya.

Escenario 5 del plan de decisión, aplicado de verdad: en vez de que un LLM lea
el documento y opine (3-5s, $0.002, sin confianza), Laya responde el set tipado
de preguntas en paralelo y devuelve probabilidades por dimensión.

    # Con Laya on-demand caliente:
    python scripts/laya_on_demand.py --python <venv-con-laya> run -- \
        python examples/ai_check_demo.py

    # O contra cualquier backend configurado:
    python examples/ai_check_demo.py --backend openrouter
    python examples/ai_check_demo.py --file mi-documento.md

Tres muestras incorporadas para que el demo corra sin argumentos:
  1. "slop"   — texto generado con los tell-tale deliberados
  2. "humano" — prosa real de la política de routing (voz fuerte, ritmo irregular)
  3. "editado" — el mismo slop pasado por una pasada de humanización
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "scripts"))

from jev_client import JEV  # noqa: E402
from jev_schemas import AI_DIMENSIONS_V1  # noqa: E402


# --------------------------------------------------------------------------- #
# Muestras
# --------------------------------------------------------------------------- #
SLOP = (
    "In today's rapidly evolving landscape, organizations must leverage robust "
    "frameworks to navigate the multifaceted challenges of digital transformation. "
    "It is important to note that comprehensive strategies facilitate seamless "
    "integration across pivotal operational domains. Furthermore, fostering a "
    "culture of continuous improvement ensures that stakeholders remain aligned "
    "with strategic objectives. Additionally, utilizing data-driven insights "
    "enables teams to streamline workflows and enhance overall efficiency. "
    "Ultimately, a holistic approach is essential for sustainable growth in an "
    "increasingly competitive environment."
)

HUMANO = (
    "Ningún modelo fuera del registro §2 y las tablas §3-§4 puede usarse, jamás, "
    "bajo ninguna circunstancia — incluso con autonomía total. Cualquier modelo "
    "que no esté explícitamente en este documento requiere la autorización "
    "explícita de Andrés ANTES de usarse. No después, no \"es solo una llamada\", "
    "no \"era el default\"."
)

EDITADO = (
    "La política tiene un límite duro: ningún modelo fuera de las tablas §2-§4 "
    "es elegible. Si algo no está listado, se para y se pregunta. La razón es que "
    "el costo de improvisar es mayor que el de esperar."
)

SAMPLES = {"slop": SLOP, "humano": HUMANO, "editado": EDITADO}

# Pesos del compuesto (mismo criterio que el skill ai-check).
WEIGHTS = {
    "has_em_dash_overuse": 0.15,
    "uses_banned_vocab": 0.25,
    "uniform_sentence_len": 0.20,
    "templated_structure": 0.15,
    "voice_consistency": 0.10,
    "human_likelihood": 0.15,
}
TEMPLATE_P = {"highly_templated": 0.9, "somewhat_templated": 0.5, "natural": 0.1}


def composite(answers: dict) -> dict:
    """0..100, donde más alto = más señales de IA."""
    g = lambda k, d=0.0: answers.get(k, {}).get("value", d)  # noqa: E731

    em = float(g("has_em_dash_overuse"))
    banned = float(g("uses_banned_vocab"))
    uniform = float(g("uniform_sentence_len"))
    templ = TEMPLATE_P.get(str(g("templated_structure", "natural")), 0.5)
    voice = float(g("voice_consistency", 3))
    human = float(g("human_likelihood", 5))

    voice_ai = max(0.0, min(1.0, (voice - 1) / 4.0))
    human_ai = max(0.0, min(1.0, (10 - human) / 9.0))

    parts = {
        "em_dash_overuse": (em, WEIGHTS["has_em_dash_overuse"]),
        "banned_vocab": (banned, WEIGHTS["uses_banned_vocab"]),
        "uniform_sentence_len": (uniform, WEIGHTS["uniform_sentence_len"]),
        "templated_structure": (templ, WEIGHTS["templated_structure"]),
        "voice_consistency": (voice_ai, WEIGHTS["voice_consistency"]),
        "human_likelihood_inv": (human_ai, WEIGHTS["human_likelihood"]),
    }
    total_w = sum(w for _, w in parts.values())
    score = sum(v * w for v, w in parts.values()) / total_w
    score100 = round(score * 100, 1)
    label = ("very_likely_human" if score100 < 20 else
             "likely_human" if score100 < 40 else
             "mixed_signals" if score100 < 60 else
             "likely_ai" if score100 < 80 else "very_likely_ai")
    return {"composite": score100, "label": label,
            "parts": {k: round(v, 3) for k, (v, _) in parts.items()}}


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Scoring de AI-tells con la capa de decisión.")
    ap.add_argument("--backend", default=None,
                    help="openrouter | vercel | typesafe | laya (default: autodetecta)")
    ap.add_argument("--file", help="Scorear un documento real en vez de las muestras.")
    ap.add_argument("--json", action="store_true", help="Salida JSON cruda.")
    args = ap.parse_args()

    client = JEV(backend=args.backend)
    print(f"# capa de decisión · backend={client.mode} · modelo={client.model}\n")

    if client.mode == "fallback":
        print("AVISO: sin backend real (mode=fallback). Los números son un stub "
              "determinista, NO una medición.\n")

    docs = {"(archivo)": Path(args.file).read_text(encoding="utf-8")} if args.file else SAMPLES

    results = {}
    for name, text in docs.items():
        v = client.classify(text, AI_DIMENSIONS_V1)
        a = v.as_dict()["answers"]
        c = composite(a)
        results[name] = {"composite": c, "answers": a,
                         "mode": v.mode, "latency_ms": v.latency_ms,
                         "cost_usd": v.cost_usd}

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    # --- tabla ---
    print(f"{'muestra':<12} {'compuesto':>10}  {'lectura':<18} {'latencia':>9}")
    print("-" * 54)
    for name, r in results.items():
        print(f"{name:<12} {r['composite']['composite']:>10}  "
              f"{r['composite']['label']:<18} {r['latency_ms']:>7}ms")

    print("\n## desglose por dimensión (0 = humano-consistente, 1 = muy IA)\n")
    dims = list(next(iter(results.values()))["composite"]["parts"])
    print(f"{'dimensión':<24}" + "".join(f"{n:>10}" for n in results))
    print("-" * (24 + 10 * len(results)))
    for d in dims:
        row = "".join(f"{results[n]['composite']['parts'][d]:>10}" for n in results)
        print(f"{d:<24}{row}")

    total_cost = sum(r["cost_usd"] for r in results.values())
    print(f"\ncosto total: ${total_cost:.6f}  ·  {len(results)} documentos  ·  backend={client.mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())