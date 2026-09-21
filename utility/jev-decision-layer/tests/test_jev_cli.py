"""Tests for jev_cli.py — subprocess entry per §12 cross-skill consumption."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "scripts" / "jev_cli.py"

ENV_CLEAN = {
    k: v
    for k, v in os.environ.items()
    if not k.startswith(("JEV_", "TYPESAFE_", "VERCEL_", "AI_GATEWAY_", "LAYA_"))
}


@pytest.fixture(autouse=True)
def _clear_real_cost_log():
    """Each CLI test spawns a subprocess that writes to the canonical cost-log.
    Wipe it before each test so cost-report assertions are deterministic.
    """
    real = SKILL_DIR / "references" / "cost-log.jsonl"
    if real.exists():
        real.unlink()


def run_cli(*args, stdin=None):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        env=ENV_CLEAN,
        input=stdin,
    )


def test_list_presets_returns_json():
    p = run_cli("list-presets")
    assert p.returncode == 0
    data = json.loads(p.stdout)
    assert "presets" in data
    assert "slide_done_v1" in data["presets"]


def test_classify_with_preset():
    p = run_cli(
        "classify",
        "--state", "the slide says all answers are filled and score is 5/5",
        "--preset", "slide_done_v1",
    )
    assert p.returncode == 0
    data = json.loads(p.stdout)
    assert data["mode"] == "fallback"  # no creds
    assert "score_at_max" in data["answers"]


def test_classify_with_inline_questions():
    p = run_cli(
        "classify",
        "--state", "deploy failed",
        "--question", 'urgent="noul:Is this urgent?"',
    )
    assert p.returncode == 0
    data = json.loads(p.stdout)
    assert "urgent" in data["answers"]


def test_classify_via_stdin():
    payload = json.dumps({
        "state": "service is down",
        "questions": {"ok": ("noul", "Is everything fine?")},
    })
    p = run_cli("classify", "--stdin", stdin=payload)
    assert p.returncode == 0
    data = json.loads(p.stdout)
    assert "ok" in data["answers"]


def test_classify_missing_state():
    p = run_cli("classify", "--preset", "slide_done_v1")
    # either nothing happens (need --state) or error
    assert p.returncode != 0 or "error" in p.stdout


def test_cost_report_empty_log():
    p = run_cli("cost-report")
    assert p.returncode == 0
    data = json.loads(p.stdout)
    assert data["calls"] == 0
    assert data["total_usd"] == 0
