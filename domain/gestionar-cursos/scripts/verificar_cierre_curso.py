"""
verificar_cierre_curso.py — auto-check "is this Moodle course fully closed?"

Combines the existing grade-report fetch with the JEV decision layer to produce
a calibrated probability the course is fully closed, plus per-question signals
the orchestrator (or a human reviewer) can act on.

Pipeline:
  1. Fetch `grade/report/user/index.php?id=<course_id>`
  2. Parse H5P activities and their final scores
  3. Serialize as a small JSON state
  4. Call `jev-decision-layer` (via jev_shim) with the `course_closed_v1` preset
  5. Apply threshold policy and emit verdict + structured log

The script is idempotent — same course+user always yields the same mode (modulo
JEV's stochasticity in live mode). When JEV is unavailable, it returns an
explicit `mode="fallback"` verdict so the orchestrator can decide whether the
heuristic is good enough or whether to require a human review.

Usage:
    python verificar_cierre_curso.py --course-id 16564 [--surface surface:9]
    python verificar_cierre_curso.py --course-id 16564 --dry-run
    python verificar_cierre_curso.py --report-json -

Subprocess, never imported (§12). Other skills delegate via shell.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------- #
# Reuse existing infra within the same skill
# --------------------------------------------------------------------------- #
_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

try:
    from jev_shim import jev_classify_inline  # noqa: F401 — surfaces the helper
    _JEV_OK = True
except Exception:
    _JEV_OK = False


# --------------------------------------------------------------------------- #
# Grade report fetcher
# --------------------------------------------------------------------------- #
GRADE_URL_TPL = "https://aulavirtual.uniremington.edu.co/grade/report/user/index.php?id={course_id}"


def _row_to_dict(row) -> dict:
    """Best-effort parse of one grade-report row into a flat dict."""
    cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
    if not cells:
        return {}
    return {
        "name": cells[0],
        "weight": cells[1] if len(cells) > 1 else "",
        "grade": cells[2] if len(cells) > 2 else "",
        "range": cells[3] if len(cells) > 3 else "",
        "percentage": cells[4] if len(cells) > 4 else "",
        "raw_cells": cells[:6],
    }


def fetch_grade_report(course_id: str, browser=None) -> dict:
    """Use the existing browser if open, else spawn a fresh requests session.

    Returns: {"rows": [...], "fetched_at": ISO, "source": str}
    """
    if browser is None:
        return _fetch_via_requests(course_id)
    return _fetch_via_browser(course_id, browser)


def _fetch_via_browser(course_id, browser) -> dict:
    browser.goto(GRADE_URL_TPL.format(course_id=course_id))
    # The grade report is rendered server-side; HTML has the table ready.
    time.sleep(1.0)
    html = browser.ev("document.documentElement.outerHTML") or {}
    if isinstance(html, dict):
        html = html.get("_raw") or json.dumps(html)
    return _parse_grade_html(str(html), source="browser")


def _fetch_via_requests(course_id: str) -> dict:
    """Headless fetch — assumes a cookie jar exists in ~/.agents/.browserdata.

    Implemented as a fall-back only; primary path is via the existing browser
    the agent already opened.
    """
    import requests
    home = Path.home() / ".agents" / ".browserdata" / "Default" / "Cookies"
    if not home.exists():
        return {"rows": [], "fetched_at": datetime.now().isoformat(timespec="seconds"),
                "source": "no-cookies", "error": "no browser session available"}
    # Real implementation would parse the Chrome cookies SQLite. Keeping a stub
    # here because the orchestrator almost always passes a browser session in.
    return {"rows": [], "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "source": "requests-stub", "error": "cookies not parsed in stub"}


def _parse_grade_html(html: str, source: str) -> dict:
    """Light HTML parse — no BeautifulSoup dep required."""
    rows: list[dict] = []
    # The Moodle grade report rows look like:
    #   <tr class="even r1"><td>Activity name</td>...<td>10,00</td><td>10,00</td>...
    for m in re.finditer(
        r"<tr[^>]*class=\"([^\"]*)\"[^>]*>(.*?)</tr>",
        html, flags=re.DOTALL | re.IGNORECASE,
    ):
        cls, body = m.group(1), m.group(2)
        if "header" in cls.lower():
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", body, flags=re.DOTALL | re.IGNORECASE)
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        if not cells:
            continue
        rows.append({
            "name": cells[0][:120],
            "weight": cells[1] if len(cells) > 1 else "",
            "grade": cells[2] if len(cells) > 2 else "",
            "range": cells[3] if len(cells) > 3 else "",
            "percentage": cells[4] if len(cells) > 4 else "",
            "row_class": cls,
        })

    return {"rows": rows, "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "source": source, "n_rows": len(rows)}


# --------------------------------------------------------------------------- #
# State shape
# --------------------------------------------------------------------------- #
def serialize_for_jev(grade_report: dict, expected_count: int | None = None) -> str:
    """Compact JSON state for the JEV course_closed_v1 preset.

    Kept small on purpose: JEV's accuracy degrades with input size for tight
    decisions, and the question being asked is bounded.
    """
    rows = grade_report.get("rows", [])
    hvp_rows = [r for r in rows if "hvp" in r.get("row_class", "").lower()
                or "h5p" in r.get("name", "").lower()]
    summary = {
        "course_id": grade_report.get("course_id"),
        "expected_activities": expected_count,
        "observed_activities": len(hvp_rows),
        "scores_compact": [r.get("grade") for r in hvp_rows[:50]],
        "percentages_compact": [r.get("percentage") for r in hvp_rows[:50]],
        "any_dash": any(r.get("grade", "") == "-" for r in hvp_rows),
        "any_below_100": any(",00" in r.get("grade", "") and r.get("grade") != "10,00"
                            for r in hvp_rows),
        "fetched_at": grade_report.get("fetched_at"),
    }
    return json.dumps(summary, separators=(",", ":"), ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Threshold policy
# --------------------------------------------------------------------------- #
DEFAULT_THRESHOLDS = {
    "todos_al_100": 0.95,        # >= this ⇒ everything at max
    "faltan_intentados_max": 0.50,  # <= this ⇒ no never-attempted items
    "hay_nota_baja_max": 0.50,      # <= this ⇒ no low grades
    "rumbo_coherente_min": 4,       # >= this ⇒ coherent completion
}


def apply_thresholds(verdict: dict, thresholds: dict | None = None) -> dict:
    """Combine JEV's per-question answers into a single closed/uncertain decision."""
    t = thresholds or DEFAULT_THRESHOLDS
    answers = verdict.get("answers", {})

    todos = answers.get("todos_al_100", {}).get("value", 0.0)
    faltan = answers.get("faltan_intentados", {}).get("value", 1.0)
    bajas = answers.get("hay_nota_baja", {}).get("value", 1.0)
    rumbo = answers.get("rumbo_coherente", {}).get("value", 0)

    closed = (
        todos >= t["todos_al_100"]
        and faltan <= t["faltan_intentados_max"]
        and bajas <= t["hay_nota_baja_max"]
        and rumbo >= t["rumbo_coherente_min"]
    )
    return {
        "closed": closed,
        "todos_al_100_p": todos,
        "faltan_intentados_p": faltan,
        "hay_nota_baja_p": bajas,
        "rumo_coherente_s": rumbo,
        "thresholds_used": t,
        "mode": verdict.get("mode", "fallback"),
        "uncertain": verdict.get("uncertain", True),
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(
        description="¿Está este curso Moodle completamente cerrado? (JEV decision layer)"
    )
    ap.add_argument("--course-id", required=True)
    ap.add_argument("--expected-count", type=int, default=None,
                    help="Si se sabe, número esperado de actividades interactivas")
    ap.add_argument("--report-json", default="-",
                    help="Path para el JSON de salida, o '-' para stdout")
    ap.add_argument("--dry-run", action="store_true",
                    help="Solo computar el state; no llamar a JEV")
    args = ap.parse_args()

    grade_report = fetch_grade_report(args.course_id)
    grade_report["course_id"] = args.course_id

    if args.dry_run:
        out = {"grade_report": grade_report, "jev_skipped": True}
        _emit(out, args.report_json)
        return 0

    if not _JEV_OK:
        out = {
            "grade_report": grade_report,
            "decision": {"closed": None, "uncertain": True,
                         "reason": "jev-decision-layer skill not installed"},
        }
        _emit(out, args.report_json)
        return 0

    state = serialize_for_jev(grade_report, args.expected_count)
    from jev_shim import _run_cli  # local import to keep imports tight
    verdict = _run_cli(state, "course_closed_v1")
    decision = apply_thresholds(verdict)
    out = {"grade_report": grade_report, "decision": decision, "state": state}
    _emit(out, args.report_json)
    return 0 if decision.get("closed") is not False else 1


def _emit(obj: dict, dest: str) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    if dest == "-":
        print(text)
    else:
        Path(dest).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
