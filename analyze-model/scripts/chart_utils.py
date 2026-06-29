"""
ASCII chart utilities for analyze-model output.

Zero-dependency rendering: horizontal bars, sparklines, gauges, comparison charts.
All functions return strings for stdout — no file writes, no external renderers.
Uses Unicode block characters where supported, falls back to ASCII.
"""

import shutil
import sys

BLOCKS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"

FULL = "\u2588"
EMPTY = "\u2591"

if sys.stdout.encoding and "utf" not in sys.stdout.encoding.lower():
    FULL = "#"
    EMPTY = "-"
    BLOCKS = None


def hbar(label: str, value: float, max_value: float,
         suffix: str = "", width: int = 40) -> str:
    """Single horizontal bar with label, bar, and value suffix."""
    term_width = min(shutil.get_terminal_size().columns - 55, width)
    term_width = max(term_width, 10)
    bar_len = int((value / max_value) * term_width) if max_value > 0 else 0
    bar_len = min(bar_len, term_width)
    bar = FULL * bar_len + EMPTY * (term_width - bar_len)
    return f"{label:<30} {bar} {suffix}"


def gauge(label: str, ratio: float, width: int = 10) -> str:
    """Efficiency gauge. Below 1.0 shows under-utilized warning."""
    filled = min(int(ratio * width), width)
    bar = FULL * filled + EMPTY * (width - filled)
    if ratio < 1.0:
        status = "under-utilized"
    elif ratio < 2.0:
        status = "efficient"
    else:
        status = "optimal"
    return f"{label:<8} {bar} {ratio:.1f}x  {status}"


def sparkline(values: list[float], label: str = "",
              width: int = 12, max_val: float | None = None) -> str:
    """Sparkline using Unicode block characters (falls back to ASCII #)."""
    if not values:
        return f"{label:<6} (no data)"
    if max_val is None:
        max_val = max(values) if max(values) else 1

    if len(values) < width:
        padded = values + [0] * (width - len(values))
    elif len(values) > width:
        step = len(values) / width
        padded = [values[int(i * step)] for i in range(width)]
    else:
        padded = values

    chars = []
    for v in padded:
        if BLOCKS:
            idx = min(int((v / max_val) * (len(BLOCKS) - 1)), len(BLOCKS) - 1)
            chars.append(BLOCKS[idx])
        else:
            ratio = v / max_val if max_val > 0 else 0
            chars.append("#" if ratio > 0.5 else "." if ratio > 0 else " ")
    spark = "".join(chars)
    return f"{label:<6} {spark} {padded[-1]:.0f}%"


def comparison(items: list[tuple[str, float, str]], width: int = 50) -> str:
    """Side-by-side horizontal bars for comparison."""
    if not items:
        return ""
    max_val = max(v for _, v, _ in items)
    return "\n".join(hbar(label, value, max_val, suffix, width)
                     for label, value, suffix in items)
