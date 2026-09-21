"""Tests for jev_schemas.py — all 6 presets must be present and well-formed."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import jev_schemas  # noqa: E402


EXPECTED_PRESETS = [
    "slide_done_v1",
    "find_words_drag_v1",
    "course_closed_v1",
    "render_gate_v1",
    "ai_dimensions_v1",
    "triage_quality_v1",
]


@pytest.mark.parametrize("name", EXPECTED_PRESETS)
def test_preset_exists(name):
    assert name in jev_schemas.PRESETS


@pytest.mark.parametrize("name", EXPECTED_PRESETS)
def test_preset_has_questions(name):
    p = jev_schemas.PRESETS[name]
    assert len(p) > 0
    for k, v in p.items():
        assert v["type"] in ("noul", "choice", "score")
        assert isinstance(v["instructions"], str)
        assert len(v["instructions"]) > 0


@pytest.mark.parametrize("name", EXPECTED_PRESETS)
def test_preset_instructions_are_short(name):
    """JEV instructions should be declarative and brief (one judgment each)."""
    p = jev_schemas.PRESETS[name]
    for k, v in p.items():
        # 1-2 sentences, no run-on
        assert len(v["instructions"]) < 280, f"{name}.{k} too long"


def test_choice_presets_have_options():
    p = jev_schemas.RENDER_GATE_V1
    assert "options" in p["render_succeeded"]
    assert len(p["render_succeeded"]["options"]) <= 255


def test_score_presets_have_range():
    p = jev_schemas.COURSE_CLOSED_V1
    for k, v in p.items():
        if v["type"] == "score":
            assert v["range_max"] >= 2


def test_list_presets():
    p = jev_schemas.list_presets()
    assert set(EXPECTED_PRESETS) <= set(p)


def test_get_preset_unknown():
    with pytest.raises(KeyError):
        jev_schemas.get_preset("does_not_exist")
