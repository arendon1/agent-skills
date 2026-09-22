"""Tests for the decision layer (jev_schemas.decide) + per-backend thresholds.

The bug these tests lock down (measured 2026-09-21): a single fixed threshold
shared across backends produces systematic false negatives, because Laya reports
probabilities on a much more conservative scale than JEV.

    Laya on a state JEV would call 0.99:   score_at_max = 0.5546
    JEV  on the same state:                ~0.99 (claimed)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import jev_schemas  # noqa: E402
from jev_schemas import decide  # noqa: E402

CLI = SCRIPTS_DIR / "jev_cli.py"
ENV_CLEAN = {
    k: v for k, v in os.environ.items()
    if not k.startswith(("JEV_", "TYPESAFE_", "VERCEL_", "AI_GATEWAY_", "LAYA_", "OPENROUTER_"))
}

# Measured answers
ANS_GOOD = {"score_at_max": {"noul": 0.5546}, "all_answers_committed": {"noul": 0.6987}}
ANS_BAD = {"score_at_max": {"noul": 0.0011}, "all_answers_committed": {"noul": 0.0977}}


# --------------------------------------------------------------------------- #
# The bug this fixes
# --------------------------------------------------------------------------- #
def test_laya_threshold_accepts_a_true_positive():
    """The measured Laya score for a genuinely complete slide must pass."""
    d = decide("slide_done_v1", ANS_GOOD, "laya", 0.40)
    assert d["decision"] == "pass", f"regression: {d}"


def test_jev_threshold_on_laya_would_be_a_false_negative():
    """Documents WHY the threshold is per-backend, not per-preset."""
    d = decide("slide_done_v1", ANS_GOOD, "laya", 0.95)
    assert d["decision"] == "fail"
    assert "score_at_max" in d["reasons"]


def test_laya_threshold_rejects_a_true_negative():
    d = decide("slide_done_v1", ANS_BAD, "laya", 0.40)
    assert d["decision"] == "fail"


# --------------------------------------------------------------------------- #
# Uncertain semantics
# --------------------------------------------------------------------------- #
def test_fallback_is_always_uncertain():
    for th in (0.4, 0.95):
        d = decide("slide_done_v1", ANS_GOOD, "fallback", th)
        assert d["decision"] == "uncertain"
        assert d["confident"] is False


def test_error_is_uncertain():
    d = decide("slide_done_v1", ANS_GOOD, "error", 0.5)
    assert d["decision"] == "uncertain"


def test_missing_threshold_is_uncertain():
    d = decide("slide_done_v1", ANS_GOOD, "laya", None)
    assert d["decision"] == "uncertain"
    assert "no_threshold_for_backend" in d["reasons"]


def test_uncertain_is_never_a_pass():
    """The load-bearing invariant: no signal must never read as approval."""
    for mode in ("fallback", "error", None):
        d = decide("slide_done_v1", {"score_at_max": {"noul": 1.0},
                                     "all_answers_committed": {"noul": 1.0}}, mode, 0.4)
        assert d["decision"] != "pass"


# --------------------------------------------------------------------------- #
# Every preset has a working rule
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("preset", [
    "slide_done_v1", "find_words_drag_v1", "course_closed_v1",
    "render_gate_v1", "triage_quality_v1",
])
def test_preset_has_a_decision_rule(preset):
    assert preset in jev_schemas.DECISION_RULES


def test_ai_dimensions_has_no_binary_rule():
    """ai_dimensions is a multi-dimension score, not a gate."""
    d = decide("ai_dimensions_v1", {"human_likelihood": {"score": 3}}, "laya", 0.4)
    assert d["decision"] == "uncertain"
    assert any("no_binary_rule" in r for r in d["reasons"])


def test_drag_rule_uses_a_slightly_lower_path_threshold():
    ok = {"start_in_viewport": {"noul": 0.9}, "end_in_viewport": {"noul": 0.9},
          "path_uninterrupted": {"noul": 0.86}}
    assert decide("find_words_drag_v1", ok, "laya", 0.90)["decision"] == "pass"
    bad = {"start_in_viewport": {"noul": 0.9}, "end_in_viewport": {"noul": 0.9},
           "path_uninterrupted": {"noul": 0.60}}
    assert decide("find_words_drag_v1", bad, "laya", 0.90)["decision"] == "fail"


def test_render_gate_needs_the_pass_choice():
    q = {"render_succeeded": {"choice": "needs_human"}, "no_visual_glitches": {"noul": 1.0}}
    assert decide("render_gate_v1", q, "laya", 0.4)["decision"] == "fail"


def test_course_closed_uses_fixed_4_for_the_score_question():
    """`rumbo_coherente` is a 1..5 score, not a probability: it goes against 4."""
    good = {"todos_al_100": {"noul": 0.8}, "faltan_intentados": {"noul": 0.05},
            "hay_nota_baja": {"noul": 0.05}, "rumbo_coherente": {"score": 5}}
    assert decide("course_closed_v1", good, "laya", 0.4)["decision"] == "pass"
    bad = dict(good, rumbo_coherente={"score": 2})
    assert decide("course_closed_v1", bad, "laya", 0.4)["decision"] == "fail"


# --------------------------------------------------------------------------- #
# CLI surface
# --------------------------------------------------------------------------- #
def _run(*args, stdin=None):
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True,
                          text=True, env=ENV_CLEAN, input=stdin)


def test_cli_decide_exit_3_on_fallback():
    p = _run("decide", "--state", "x", "--preset", "slide_done_v1", "--backend", "fallback")
    assert p.returncode == 3, p.stdout
    assert json.loads(p.stdout)["decision"] == "uncertain"


def test_cli_decide_with_explicit_threshold_and_no_signal_is_uncertain():
    p = _run("decide", "--state", "x", "--preset", "slide_done_v1",
             "--backend", "fallback", "--threshold", "0.4")
    assert json.loads(p.stdout)["decision"] == "uncertain"


def test_cli_threshold_comes_from_config_per_backend():
    """The CLI must read thresholds_by_backend rather than assuming one value."""
    src = (SCRIPTS_DIR / "jev_cli.py").read_text()
    assert "thresholds_by_backend" in src
    from jev_cli import threshold_for
    assert threshold_for("laya") == 0.40
    assert threshold_for("typesafe") == 0.95
    assert threshold_for("openrouter") == 0.75
    assert threshold_for("unknown_backend") is None


# --------------------------------------------------------------------------- #
# REGRESIÓN: el CLI construía las preguntas como (type, instructions) y perdía
# `options` / `range_max` — rompía 4 de los 6 presets con "options required".
# --------------------------------------------------------------------------- #
ALL_PRESETS = [
    "slide_done_v1", "find_words_drag_v1", "course_closed_v1",
    "render_gate_v1", "ai_dimensions_v1", "triage_quality_v1",
]


@pytest.mark.parametrize("preset", ALL_PRESETS)
def test_every_preset_survives_the_cli(preset):
    p = _run("decide", "--state", "estado de prueba", "--preset", preset,
             "--backend", "fallback")
    assert p.returncode in (0, 1, 3), f"{preset} crasheó:\n{p.stderr}"
    d = json.loads(p.stdout)
    assert d["decision"] in ("pass", "fail", "uncertain")
    assert d["answers"], f"{preset} no devolvió respuestas"


@pytest.mark.parametrize("preset", ALL_PRESETS)
def test_choice_and_score_questions_keep_their_metadata(preset):
    """El dict del preset debe llegar COMPLETO, no recortado."""
    from jev_cli import build_questions
    import argparse
    q = build_questions(argparse.Namespace(preset=preset, question=[]))
    for k, v in q.items():
        if v["type"] == "choice":
            assert v.get("options") or v.get("criteria"), f"{preset}.{k}: choice sin opciones"
        if v["type"] == "score":
            assert v.get("range_max"), f"{preset}.{k}: score sin range_max"


# --------------------------------------------------------------------------- #
# Política de backend — "usá Laya cuando corresponda"
# --------------------------------------------------------------------------- #
def test_backend_policy_prefers_laya_for_guardrails():
    from jev_cli import resolve_backend
    import jev_cli
    orig = jev_cli.probe_backend
    jev_cli.probe_backend = lambda n: n == "laya"      # simulamos Laya viva
    try:
        chosen, trace = resolve_backend("slide_done_v1")
        assert chosen == "laya"
        assert trace[0] == {"backend": "laya", "available": True}
    finally:
        jev_cli.probe_backend = orig


def test_backend_policy_falls_through_and_leaves_a_trace():
    from jev_cli import resolve_backend
    import jev_cli
    orig = jev_cli.probe_backend
    jev_cli.probe_backend = lambda n: n == "openrouter"        # Laya apagada
    try:
        chosen, trace = resolve_backend("slide_done_v1")
        assert chosen == "openrouter"
        assert trace[0] == {"backend": "laya", "available": False}
        assert any(t["backend"] == "openrouter" and t["available"] for t in trace)
    finally:
        jev_cli.probe_backend = orig


def test_backend_policy_excludes_laya_for_stylistic_judgement():
    """ai_dimensions_v1 no va con Laya (medido: salía invertido)."""
    from jev_cli import _load_thresholds  # noqa: F401  (fuerza el import del módulo)
    import jev_cli
    from jev_client import _load_config
    policy = (_load_config() or {}).get("backend_policy", {})
    assert "laya" not in policy.get("ai_dimensions_v1", [])
    assert policy.get("slide_done_v1", [])[:1] == ["laya"]


def test_probe_backend_reports_fallback_available():
    from jev_cli import probe_backend
    assert probe_backend("fallback") is True
    assert probe_backend("no_existe") is False