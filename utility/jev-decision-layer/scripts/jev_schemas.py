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
