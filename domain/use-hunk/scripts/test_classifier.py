#!/usr/bin/env python3
"""Smoke test for the use-hunk resume classifier.

Runs the canonical cases from PLAN.md T6 against the lexicon defined
in references/lexicon.md. Exits 0 when all match, 1 otherwise. Run
this after editing the classifier or the lexicons; the algorithm in
references/lexicon.md and the cases here must stay in lockstep.

Usage:
  python3 scripts/test_classifier.py
"""
from __future__ import annotations

import re
import sys

# ---------------------------------------------------------------------------
# Lexicons (mirrors references/lexicon.md)
# ---------------------------------------------------------------------------

APPROVE: set[str] = {
    # Spanish
    "dale", "va", "vamos", "sigue", "procede", "adelante", "ok", "listo",
    "confirmado", "aprobado", "hecho", "por favor continua", "continúa",
    "continua", "next", "siguiente",
    # English
    "go", "okay", "continue", "proceed", "ship", "ship it", "lgtm",
    "looks good", "approved", "confirmed", "done", "yep", "yeah",
    "sure", "merge", "commit", "push",
    # Single-char / emoji
    "✓", "✔", "👍", "+1", "thumbs up",
}

STOP: set[str] = {
    # Spanish
    "cancelar", "cancela", "abort", "aborta", "abortar", "rollback",
    "revierte", "revertir", "deshaz", "para", "detén", "deten", "stop",
    "alto", "no", "rechaza", "rechazado",
    # English
    "cancel", "abort", "rollback", "revert", "undo", "stop", "halt",
    "no", "rejected", "denied", "scratch", "scrap", "kill",
}

# Verb stems — match `stem\w*` with a word boundary. Covers English
# (rename, change, use, move, ...) and Spanish (cambia, renombra, usa, ...).
# Adding a stem here lets the classifier catch all conjugations of the verb.
VERB_STEMS: set[str] = {
    # English
    "renam", "chang", "mov", "extract", "delet", "remov",
    "add", "fix", "refactor", "split", "merg", "replac", "switch",
    "swap", "drop", "keep", "mak", "set", "put", "writ", "tri",
    "attempt", "flip", "implement", "introduc",
    # Spanish
    "cambi", "renombr", "haz", "muev", "extra", "borr", "elimin",
    "añad", "agreg", "arregl", "refactoriz", "divid", "fusion",
    "reemplaz", "sustituy", "intercambi", "manten", "escrib", "intent",
    "introduc", "quit", "pon", "met", "sac",
    # English "use" / Spanish "usar" / "us" pronoun — "us" stem matches
    # all conjugations (use, uses, using, used; usa, usas, usando).
    # The pronoun "us" false-positives are absorbed by the question check
    # that runs first (e.g. "for us?" is a question, not an instruction).
    "us",
}

INSTRUCTION_VERBS = re.compile(
    r"\b(" + "|".join(sorted(VERB_STEMS, key=len, reverse=True)) + r")\w*\b",
    re.IGNORECASE,
)

CHANGE_QUESTION = re.compile(
    r"\?$|\b("
    r"did\s+you|do\s+you|why|what\s+does|what\s+is|"
    r"is\s+.*\s+correct|should\s+we|should\s+i|are\s+you\s+sure|"
    r"is\s+this|is\s+that|really|shouldn't"
    r")\b",
    re.IGNORECASE,
)

CODE_TOKEN = re.compile(
    r"`[^`]+`|function\s*\(|class\s+\w+\s*:|"
    r"\{[^}]*\}|"
    r"\w+\.(py|ts|js|tsx|jsx|go|rs|java|rb|swift|kt):\d+|"
    r"^\s*[+-]\s",
    re.MULTILINE,
)
ALTERNATIVE = re.compile(
    r"\binstead\s+of\b|\brather\s+than\b|\bwould\s+prefer\b|"
    r"\bprefiero\b|\bmejor\s+con\b|\binstead\b",
    re.IGNORECASE,
)
DECLARATIVE = re.compile(
    r"^(the|this|we|it|esto|esto)\s+\w+\s+(should|deber)|"
    r"^(necesitamos|we\s+need|hay\s+que)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tokenize(msg: str) -> list[str]:
    return [t for t in re.split(r"[\s,;.!¿¡:]+", msg.lower()) if t]


def looks_like_change_question(msg: str) -> bool:
    return bool(CHANGE_QUESTION.search(msg))


def looks_like_instruction(msg: str) -> bool:
    return bool(
        INSTRUCTION_VERBS.search(msg)
        or CODE_TOKEN.search(msg)
        or ALTERNATIVE.search(msg)
        or DECLARATIVE.search(msg)
    )


def classify(message: str) -> str:
    """Resume classifier — returns one of: approve | feedback | stop | ambiguous.

    Precedence (from references/lexicon.md):
        question > instruction > stop > approve > ambiguous
    """
    msg = message.lower().strip()
    if not msg:
        return "ambiguous"

    # 1. question about the change → ambiguous FIRST
    if looks_like_change_question(msg):
        return "ambiguous"

    # 2. instruction-shaped → feedback BEFORE stop
    if looks_like_instruction(msg):
        return "feedback"

    # 3. any token matches stop
    tokens = tokenize(msg)
    if any(t in STOP for t in tokens):
        return "stop"

    # 4. any token matches approve
    if any(t in APPROVE for t in tokens):
        return "approve"

    # 5. exact match (single-token or whole-phrase)
    if msg in APPROVE:
        return "approve"
    if msg in STOP:
        return "stop"

    return "ambiguous"


# ---------------------------------------------------------------------------
# Test cases — keep in lockstep with the algorithm above
# ---------------------------------------------------------------------------

CASES: list[tuple[str, str, str]] = [
    # T6 scenarios from PLAN.md
    ("go", "approve", "T6: operator says 'go' after pause"),
    ("dale", "approve", "T6: Spanish 'dale'"),
    ("rename Y to Z", "feedback", "T6: feedback 'rename Y to Z'"),
    ("use approach Q instead", "feedback", "T6: feedback with alternative"),
    ("hmm", "ambiguous", "T6: operator types 'hmm'"),
    ("aborta", "stop", "T6: 'aborta'"),
    # Edge cases
    ("", "ambiguous", "edge: empty message"),
    ("?", "ambiguous", "edge: just a question mark"),
    ("✓", "approve", "edge: checkmark emoji"),
    ("👍", "approve", "edge: thumbs up emoji"),
    ("+1", "approve", "edge: +1"),
    ("thanks", "ambiguous", "edge: 'thanks' alone is NOT approval"),
    ("thanks, but rename the helper to foo", "feedback", "edge: thanks + actual feedback"),
    ("dale go", "approve", "edge: mixed languages, approve token wins"),
    ("Stop changing the file", "feedback", "edge: 'stop' mid-sentence, whole is feedback"),
    ("Did you really change X?", "ambiguous", "edge: question about the change"),
    ("the helper should use kebab-case", "feedback", "edge: declarative 'the X should Y'"),
    ("esto está mal, usa opción B", "feedback", "edge: Spanish feedback with imperative"),
    ("auto", "ambiguous", "edge: 'auto' after pause is ambiguous (trigger override)"),
    ("lgtm", "approve", "edge: lgtm"),
    ("ship it", "approve", "edge: 'ship it'"),
    ("rollback", "stop", "edge: 'rollback'"),
    ("para", "stop", "edge: 'para' is in STOP lexicon (vs. operator 'pausa' keyword)"),
    ("sigue", "approve", "edge: 'sigue'"),
    ("deshaz", "stop", "edge: 'deshaz'"),
    ("skip-review", "ambiguous", "edge: 'skip-review' after pause is ambiguous"),
    ("refactor this to use generics", "feedback", "edge: imperative verb (English)"),
    ("use `useState` instead", "feedback", "edge: backticks (code token)"),
    # Conjugated verbs
    ("changing this would be better", "feedback", "edge: -ing form matches verb stem"),
    ("renamed the helper to foo", "feedback", "edge: -ed form matches verb stem"),
]


def main() -> int:
    fails: list[tuple[str, str, str, str]] = []
    for msg, expected, desc in CASES:
        got = classify(msg)
        status = "PASS" if got == expected else "FAIL"
        if got != expected:
            fails.append((msg, expected, got, desc))
        print(
            f"  {status}  classify({msg!r:42}) -> {got:9}  "
            f"(expected {expected:9})  {desc}"
        )
    print()
    total = len(CASES)
    print(f"Total: {total} cases, {total - len(fails)} passed, {len(fails)} failed")
    if fails:
        print("\nFAILURES:")
        for msg, expected, got, desc in fails:
            print(f"  - {msg!r}: expected {expected}, got {got}  ({desc})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
