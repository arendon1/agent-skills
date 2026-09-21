"""Unit tests for jev_client.py — focused on fallback behavior + schema validation.

These tests deliberately don't hit the network. They verify:
- Fallback returns deterministic answers when no key is set
- Question normalization works for all 3 input shapes
- Schema validation rejects malformed inputs
- Cost ledger is written regardless of mode
- Mode auto-detection picks the right backend from env
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import jev_client  # noqa: E402
from jev_client import JEV  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_real_cost_log():
    """Make sure the canonical cost-log.jsonl is empty before each test.

    Most tests use `clean_env` to redirect writes to a tmp file, but a few
    (e.g. cost_report_empty_log) hit the canonical path via subprocess.
    """
    real = SKILL_DIR / "references" / "cost-log.jsonl"
    if real.exists():
        real.unlink()


@pytest.fixture
def clean_env(monkeypatch):
    """Strip all JEV-related env vars and use a tmp cost log."""
    for k in list(os.environ):
        if k.startswith(("JEV_", "TYPESAFE_", "VERCEL_", "AI_GATEWAY_", "LAYA_", "OPENROUTER_")):
            monkeypatch.delenv(k, raising=False)
    tmp_log = SKILL_DIR / "references" / "cost-log.test.jsonl"
    monkeypatch.setattr(jev_client, "COST_LOG", tmp_log)
    if tmp_log.exists():
        tmp_log.unlink()
    yield tmp_log
    if tmp_log.exists():
        tmp_log.unlink()


# --------------------------------------------------------------------------- #
# Fallback mode
# --------------------------------------------------------------------------- #
def test_no_credentials_falls_back(clean_env):
    c = JEV()
    assert c.mode == "fallback"
    v = c.classify("hello", {"ok": ("noul", "is this ok?")})
    assert v.mode == "fallback"
    assert "ok" in v.answers
    a = v.answers["ok"]
    assert 0.0 <= a.value <= 1.0
    assert v.cost_usd == 0.0


def test_fallback_is_deterministic(clean_env):
    c = JEV()
    v1 = c.classify("state-X", {"a": ("noul", "Q")})
    v2 = c.classify("state-X", {"a": ("noul", "Q")})
    assert v1.answers["a"].value == v2.answers["a"].value


def test_fallback_different_states_differ(clean_env):
    c = JEV()
    v1 = c.classify("state-X", {"a": ("noul", "Q")})
    v2 = c.classify("state-Y", {"a": ("noul", "Q")})
    # not strictly required to differ, but in practice md5 will
    assert v1.answers["a"].value != v2.answers["a"].value


def test_fallback_choice_returns_first_option(clean_env):
    c = JEV()
    v = c.classify("x", {"pick": ("choice", "pick one", ["alpha", "beta", "gamma"])})
    assert v.answers["pick"].value == "alpha"


def test_fallback_score_returns_midpoint(clean_env):
    c = JEV()
    v = c.classify("x", {"rate": ("score", "rate", 5)})
    assert v.answers["rate"].value == 2  # floor(5/2)


# --------------------------------------------------------------------------- #
# Question normalization
# --------------------------------------------------------------------------- #
def test_normalize_tuple_sugar(clean_env):
    c = JEV()
    qs = c._normalize_questions({"a": ("noul", "Q1"), "b": ("choice", "Q2", ["x", "y"])})
    assert qs["a"]["type"] == "noul"
    assert qs["b"]["type"] == "choice"
    assert qs["b"]["options"] == ["x", "y"]


def test_normalize_dict_form(clean_env):
    c = JEV()
    qs = c._normalize_questions({
        "a": {"type": "noul", "instructions": "Q"},
        "b": {"type": "score", "instructions": "Q", "range_max": 7},
    })
    assert qs["a"]["type"] == "noul"
    assert qs["b"]["range_max"] == 7


def test_normalize_question_objects(clean_env):
    c = JEV()
    qs = c._normalize_questions([
        jev_client.Question("a", "noul", "Q1"),
        jev_client.Question("b", "choice", "Q2", options=["x", "y"]),
    ])
    assert qs["a"]["type"] == "noul"
    assert qs["b"]["options"] == ["x", "y"]


def test_rejects_choice_without_options(clean_env):
    c = JEV()
    with pytest.raises(ValueError, match="options required"):
        c._normalize_questions({"a": ("choice", "Q")})


def test_rejects_choice_too_many_options(clean_env):
    c = JEV()
    opts = [f"opt{i}" for i in range(300)]
    with pytest.raises(ValueError, match="max 255"):
        c._normalize_questions({"a": ("choice", "Q", opts)})


def test_rejects_score_without_range(clean_env):
    c = JEV()
    with pytest.raises(ValueError, match="range_max required"):
        c._normalize_questions({"a": ("score", "Q")})


def test_rejects_unknown_type(clean_env):
    c = JEV()
    with pytest.raises(ValueError, match="unknown type"):
        c._normalize_questions({"a": ("weird", "Q")})


# --------------------------------------------------------------------------- #
# Backend detection
# --------------------------------------------------------------------------- #
def test_fallback_when_no_env(clean_env):
    assert JEV()._auto_detect() == "fallback"


def test_detect_vercel_with_key(clean_env):
    os.environ["VERCEL_API_KEY"] = "test"
    assert JEV()._auto_detect() == "vercel"


def test_detect_typesafe_with_key(clean_env):
    os.environ["TYPESAFE_API_KEY"] = "test"
    assert JEV()._auto_detect() == "typesafe"


def test_detect_laya_with_base_url(clean_env):
    os.environ["JEV_BASE_URL"] = "http://localhost:9999"
    assert JEV()._auto_detect() == "laya"


# --------------------------------------------------------------------------- #
# OpenRouter backend (authorized egress host)
# --------------------------------------------------------------------------- #
def test_detect_openrouter_with_key(clean_env):
    os.environ["OPENROUTER_API_KEY"] = "test"
    assert JEV()._auto_detect() == "openrouter"


def test_openrouter_wins_over_new_egress_hosts(clean_env):
    """OpenRouter is Tier-1 allowlisted; Vercel/TypeSafe are new egress."""
    os.environ["OPENROUTER_API_KEY"] = "test"
    os.environ["VERCEL_API_KEY"] = "test"
    os.environ["TYPESAFE_API_KEY"] = "test"
    assert JEV()._auto_detect() == "openrouter"


def test_local_laya_wins_over_openrouter(clean_env):
    """No egress at all beats an authorized host."""
    os.environ["JEV_BASE_URL"] = "http://localhost:8000"
    os.environ["OPENROUTER_API_KEY"] = "test"
    assert JEV()._auto_detect() == "laya"


def test_openrouter_backend_constructed(clean_env):
    os.environ["OPENROUTER_API_KEY"] = "test-key"
    c = JEV()
    assert c.mode == "openrouter"
    assert c.model == "deepseek/deepseek-v4-flash-0731"
    assert c.price_per_1m == 0.065
    assert c.price_out_per_1m == 0.18


def test_openrouter_parses_response(clean_env, monkeypatch):
    os.environ["OPENROUTER_API_KEY"] = "test"
    c = JEV()

    class FakeResp:
        status_code = 200

        def json(self):
            return {
                "choices": [{"message": {"content": json.dumps({
                    "urgent": 0.93, "route": "billing", "quality": 4,
                })}}],
                "usage": {"prompt_tokens": 800, "completion_tokens": 20},
            }

    import jev_client
    monkeypatch.setattr(jev_client.requests, "post", lambda *a, **kw: FakeResp())

    v = c.classify("state", {
        "urgent": ("noul", "is it urgent?"),
        "route": ("choice", "which?", ["billing", "tech", "other"]),
        "quality": ("score", "rate", 5),
    })
    assert v.mode == "openrouter"
    assert v.answers["urgent"].value == 0.93
    assert v.answers["route"].value == "billing"
    assert v.answers["quality"].value == 4
    assert v.tokens_in == 800
    assert v.cost_usd > 0  # charged both input and output


def test_openrouter_clamps_out_of_range(clean_env, monkeypatch):
    """An uncalibrated model may emit nonsense; the client must bound it."""
    os.environ["OPENROUTER_API_KEY"] = "test"
    c = JEV()

    class FakeResp:
        status_code = 200

        def json(self):
            return {
                "choices": [{"message": {"content": json.dumps({
                    "urgent": 7.5, "route": "nope", "quality": 99,
                })}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }

    import jev_client
    monkeypatch.setattr(jev_client.requests, "post", lambda *a, **kw: FakeResp())

    v = c.classify("state", {
        "urgent": ("noul", "q"),
        "route": ("choice", "q", ["a", "b"]),
        "quality": ("score", "q", 5),
    })
    assert v.answers["urgent"].value == 1.0        # clamped from 7.5
    assert v.answers["route"].value == "a"         # rejected → first option
    assert v.answers["quality"].value == 5         # clamped from 99


def test_openrouter_http_error_falls_back(clean_env, monkeypatch):
    os.environ["OPENROUTER_API_KEY"] = "test"
    c = JEV()

    class FakeResp:
        status_code = 429
        text = "rate limited"

        def json(self):
            return {}

    import jev_client
    monkeypatch.setattr(jev_client.requests, "post", lambda *a, **kw: FakeResp())

    v = c.classify("state", {"ok": ("noul", "q")})
    assert v.mode == "fallback"
    assert "429" in (v.error or "")


def test_openrouter_malformed_falls_back(clean_env, monkeypatch):
    os.environ["OPENROUTER_API_KEY"] = "test"
    c = JEV()

    class FakeResp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "not json at all"}}]}

    import jev_client
    monkeypatch.setattr(jev_client.requests, "post", lambda *a, **kw: FakeResp())

    v = c.classify("state", {"ok": ("noul", "q")})
    assert v.mode == "fallback"
    assert "malformed" in (v.error or "")


def test_explicit_backend_overrides_env(clean_env):
    os.environ["VERCEL_API_KEY"] = "test"
    c = JEV(backend="fallback")
    assert c.mode == "fallback"


def test_strict_raises_on_missing_key(clean_env):
    with pytest.raises(RuntimeError, match="STRICT"):
        JEV(strict=True)


# --------------------------------------------------------------------------- #
# Cost ledger
# --------------------------------------------------------------------------- #
def test_cost_log_written_in_fallback(clean_env):
    c = JEV()
    c.classify("x", {"a": ("noul", "Q")})
    assert clean_env.exists()
    lines = [l for l in clean_env.read_text().splitlines() if l]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["mode"] == "fallback"
    assert "ts" in rec
    assert rec["questions"] == 1


def test_cost_log_appends_not_overwrites(clean_env):
    c = JEV()
    c.classify("x", {"a": ("noul", "Q")})
    c.classify("y", {"b": ("noul", "Q")})
    lines = [l for l in clean_env.read_text().splitlines() if l]
    assert len(lines) == 2


# --------------------------------------------------------------------------- #
# Token estimation
# --------------------------------------------------------------------------- #
def test_estimate_tokens_string():
    assert JEV._estimate_tokens("hello") == 1
    assert JEV._estimate_tokens("a" * 400) == 100


def test_estimate_tokens_dict():
    assert JEV._estimate_tokens({"a": 1, "b": "longstringhere"}) > 0


# --------------------------------------------------------------------------- #
# Verdict ergonomics
# --------------------------------------------------------------------------- #
def test_verdict_getitem(clean_env):
    c = JEV()
    v = c.classify("x", {"a": ("noul", "Q")})
    a = v["a"]
    assert a.key == "a"
    assert a.type == "noul"


def test_verdict_as_dict_roundtrip(clean_env):
    c = JEV()
    v = c.classify("x", {"a": ("noul", "Q")})
    d = v.as_dict()
    assert d["mode"] == "fallback"
    assert d["answers"]["a"]["value"] == v.answers["a"].value
