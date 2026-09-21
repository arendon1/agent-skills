"""
JEV Decision Layer — preset question schemas.

Each preset is a fixed dictionary of `key -> {type, instructions, ...}` so callers
don't have to construct questions from scratch every time. Keep instructions
short, declarative, and contain exactly ONE judgment each.
"""

from __future__ import annotations

from typing import Any


def _noul(instructions: str) -> dict[str, Any]:
    return {"type": "noul", "instructions": instructions}


def _choice(instructions: str, options: list[str]) -> dict[str, Any]:
    return {"type": "choice", "instructions": instructions, "options": options}


def _score(instructions: str, range_max: int) -> dict[str, Any]:
    return {"type": "score", "instructions": instructions, "range_max": range_max}


# --------------------------------------------------------------------------- #
# Scenario 1: H5P slide "did this score max?"
# --------------------------------------------------------------------------- #
SLIDE_DONE_V1 = {
    "score_at_max": _noul(
        "Did this slide achieve its maximum possible score based on the DOM state, "
        "answered markers, and numeric score visible?"
    ),
    "all_answers_committed": _noul(
        "Were all required answers placed correctly (no missing or pending inputs)?"
    ),
}


# --------------------------------------------------------------------------- #
# Scenario 2: FindTheWords drag safety (H5P canvas)
# --------------------------------------------------------------------------- #
FIND_WORDS_DRAG_V1 = {
    "start_in_viewport": _noul(
        "Does the drag START point fall fully inside the canvas viewport (both axes)?"
    ),
    "end_in_viewport": _noul(
        "Does the drag END point fall fully inside the canvas viewport (both axes)?"
    ),
    "path_uninterrupted": _noul(
        "Will the straight line from start to end cross only canvas cells "
        "(not the iframe border or off-canvas area)?"
    ),
}


# --------------------------------------------------------------------------- #
# Scenario 3: Course completion check
# --------------------------------------------------------------------------- #
COURSE_CLOSED_V1 = {
    "todos_al_100": _noul(
        "Are all listed H5P activities at exactly 10.00 (not '-', not below 10.00)?"
    ),
    "faltan_intentados": _noul(
        "Is any activity showing '-' (never attempted) in the grade report?"
    ),
    "hay_nota_baja": _noul(
        "Is any activity below the expected passing threshold in the grade report?"
    ),
    "rumbo_coherente": _score(
        "Rate this course's completion coherence: 1 = clearly incomplete, "
        "5 = unambiguously fully closed",
        range_max=5,
    ),
}


# --------------------------------------------------------------------------- #
# Scenario 4: Video render quality gate
# --------------------------------------------------------------------------- #
RENDER_GATE_V1 = {
    "render_succeeded": _choice(
        "Verdict on render quality from the composition metadata + frame samples.",
        ["pass", "needs_re_render", "needs_human"],
    ),
    "captions_aligned": _noul(
        "Are captions properly aligned with audio (no drift > 100ms)?"
    ),
    "no_visual_glitches": _noul(
        "Are there visual glitches, clipping, or empty frames in this render?"
    ),
}


# --------------------------------------------------------------------------- #
# Scenario 5: AI-tell multi-dimension (ai-check re-arquitecturado)
# --------------------------------------------------------------------------- #
AI_DIMENSIONS_V1 = {
    "has_em_dash_overuse": _noul(
        "Does this text overuse em-dashes compared to a human baseline?"
    ),
    "uses_banned_vocab": _noul(
        "Does it use the AI-tell vocabulary list (delve, leverage, robust, comprehensive, "
        "streamline, foster, facilitate, pivotal, nuanced, notable, multifaceted)?"
    ),
    "uniform_sentence_len": _noul(
        "Is the sentence-length distribution suspiciously uniform (low variance)?"
    ),
    "templated_structure": _choice(
        "How templated is the structure?",
        ["highly_templated", "somewhat_templated", "natural"],
    ),
    "voice_consistency": _score(
        "How consistent is the author's voice across paragraphs? 1 = jarring shifts, "
        "5 = single coherent voice",
        range_max=5,
    ),
    "human_likelihood": _score(
        "Overall: how likely is this human-written? 1 = clearly AI, 10 = clearly human",
        range_max=10,
    ),
}


# --------------------------------------------------------------------------- #
# Scenario 6: Research output triage
# --------------------------------------------------------------------------- #
TRIAGE_QUALITY_V1 = {
    "answer_addresses_question": _noul(
        "Does this answer the question that was originally asked?"
    ),
    "sources_are_cited": _noul(
        "Are sources explicitly cited (URLs, paper titles, named authors)?"
    ),
    "confidence_in_finding": _score(
        "How confident are you in the finding? 1 = speculation, 5 = firmly grounded",
        range_max=5,
    ),
    "needs_followup": _choice(
        "Should we send a follow-up query?",
        ["yes_urgent", "yes_nice", "no"],
    ),
}


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "slide_done_v1": SLIDE_DONE_V1,
    "find_words_drag_v1": FIND_WORDS_DRAG_V1,
    "course_closed_v1": COURSE_CLOSED_V1,
    "render_gate_v1": RENDER_GATE_V1,
    "ai_dimensions_v1": AI_DIMENSIONS_V1,
    "triage_quality_v1": TRIAGE_QUALITY_V1,
}


def get_preset(name: str) -> dict[str, dict[str, Any]]:
    if name not in PRESETS:
        raise KeyError(f"unknown preset: {name} (known: {list(PRESETS)})")
    return PRESETS[name]


def list_presets() -> list[str]:
    return list(PRESETS)


# --------------------------------------------------------------------------- #
# Decision rules
# --------------------------------------------------------------------------- #
# A decision rule turns a dict of raw answers into a pass/fail/uncertain verdict,
# given a threshold. The threshold is NOT part of the rule: it is a property of
# the BACKEND. A calibrated System One model and a schema-constrained LLM report
# probabilities on very different scales (measured: Laya 0.55 on a state where
# JEV would say 0.99). See jev.json -> thresholds_by_backend.
# --------------------------------------------------------------------------- #
def _num(answers: dict, key: str, default: float = 0.0) -> float:
    a = answers.get(key) or {}
    v = a.get("noul", a.get("value"))
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _val(answers: dict, key: str, default: Any = None) -> Any:
    a = answers.get(key) or {}
    for k in ("choice", "score", "noul", "value"):
        if k in a:
            return a[k]
    return default


def _rule_slide_done(answers: dict, th: float) -> tuple[bool, list[str]]:
    sa = _num(answers, "score_at_max")
    aa = _num(answers, "all_answers_committed")
    ok = sa >= th and aa >= th
    why = []
    if sa < th:
        why.append("score_at_max")
    if aa < th:
        why.append("all_answers_committed")
    return ok, why


def _rule_drag_safe(answers: dict, th: float) -> tuple[bool, list[str]]:
    s = _num(answers, "start_in_viewport")
    e = _num(answers, "end_in_viewport")
    p = _num(answers, "path_uninterrupted")
    path_th = max(0.0, th - 0.05)
    ok = s >= th and e >= th and p >= path_th
    why = []
    if s < th:
        why.append("start_in_viewport")
    if e < th:
        why.append("end_in_viewport")
    if p < path_th:
        why.append("path_uninterrupted")
    return ok, why


def _rule_course_closed(answers: dict, th: float) -> tuple[bool, list[str]]:
    todos = _num(answers, "todos_al_100")
    faltan = _num(answers, "faltan_intentados", 1.0)
    bajas = _num(answers, "hay_nota_baja", 1.0)
    rumbo = _val(answers, "rumbo_coherente", 0)
    try:
        rumbo = float(rumbo)
    except (TypeError, ValueError):
        rumbo = 0.0
    # `rumbo_coherente` es un score 1..5, no una probabilidad: va contra 4 fijo.
    fails = 1 - th
    ok = todos >= th and faltan <= fails and bajas <= fails and rumbo >= 4
    why = []
    if todos < th:
        why.append("todos_al_100")
    if faltan > fails:
        why.append("faltan_intentados")
    if bajas > fails:
        why.append("hay_nota_baja")
    if rumbo < 4:
        why.append("rumbo_coherente")
    return ok, why


def _rule_render_gate(answers: dict, th: float) -> tuple[bool, list[str]]:
    choice = _val(answers, "render_succeeded")
    glitch = _num(answers, "no_visual_glitches")
    glitch_th = max(0.0, th - 0.05)
    ok = choice == "pass" and glitch >= glitch_th
    why = []
    if choice != "pass":
        why.append(f"choice={choice}")
    if glitch < glitch_th:
        why.append("no_visual_glitches")
    return ok, why


def _rule_triage_quality(answers: dict, th: float) -> tuple[bool, list[str]]:
    addr = _num(answers, "answer_addresses_question")
    needs = _val(answers, "needs_followup", "no")
    addr_th = max(0.0, th - 0.15)
    ok = addr >= addr_th and needs != "yes_urgent"
    why = []
    if addr < addr_th:
        why.append("answer_addresses_question")
    if needs == "yes_urgent":
        why.append("needs_followup=yes_urgent")
    return ok, why


DECISION_RULES = {
    "slide_done_v1": _rule_slide_done,
    "find_words_drag_v1": _rule_drag_safe,
    "course_closed_v1": _rule_course_closed,
    "render_gate_v1": _rule_render_gate,
    "triage_quality_v1": _rule_triage_quality,
    # ai_dimensions_v1 tiene un scoring multi-dimension, no un verdict binario.
}


def decide(preset: str, answers: dict, mode: str, threshold: float | None = None) -> dict:
    """Apply the preset's decision rule with a backend-appropriate threshold.

    Returns {"decision": "pass"|"fail"|"uncertain", "confident": bool,
             "threshold": float|None, "reasons": [...], "mode": str}.

    `uncertain` se devuelve siempre que el backend sirvio un fallback (sin senal
    real) o no hay umbral para ese backend. Los consumidores NUNCA deben tratar
    `uncertain` como un pass.
    """
    if mode in ("fallback", "error") or mode is None:
        return {"decision": "uncertain", "confident": False,
                "threshold": threshold, "reasons": [f"mode={mode}"], "mode": mode}
    rule = DECISION_RULES.get(preset)
    if rule is None:
        return {"decision": "uncertain", "confident": False,
                "threshold": threshold, "reasons": [f"no_binary_rule:{preset}"],
                "mode": mode}
    if threshold is None:
        return {"decision": "uncertain", "confident": False,
                "threshold": None, "reasons": ["no_threshold_for_backend"],
                "mode": mode}
    ok, why = rule(answers, float(threshold))
    return {"decision": "pass" if ok else "fail", "confident": bool(ok),
            "threshold": float(threshold), "reasons": why, "mode": mode}
