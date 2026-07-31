# Lexicon — classifying the operator's next message

The agent's resume classifier. After every pause, the operator's first
message MUST be classified into one of four buckets BEFORE any state
change. When classification is uncertain, the agent flags ambiguity and
asks. It never guesses.

## The four buckets

| Bucket | Triggers action | Examples |
|---|---|---|
| **approve** | next step (commit / push / hand back) | "go", "ok", "sigue", "dale", "ship", "lgtm", "✓", "+1" |
| **feedback** | iterate on the change; re-pause at end | "rename Y to Z", "use approach Q instead", "esto está mal" |
| **stop** | revert (git restore) + acknowledge | "abort", "rollback", "para", "cancela", "deshaz" |
| **ambiguous** | FLAG, ask, no state change | "hmm", "?", "ok idk", anything that doesn't match and isn't instruction-shaped |

## Approve lexicon (case-insensitive, trimmed)

Spanish:
- `dale`, `va`, `vamos`, `sigue`, `procede`, `adelante`, `ok`,
  `listo`, `confirmado`, `aprobado`, `hecho`, `✓`, `👍`, `+1`,
  `por favor continua`, `continúa`, `continua`, `next`, `siguiente`

English:
- `go`, `ok`, `okay`, `continue`, `proceed`, `ship`, `ship it`,
  `lgtm`, `looks good`, `approved`, `confirmed`, `done`, `next`,
  `+1`, `✓`, `👍`, `thumbs up`, `yep`, `yeah`, `sure`, `merge`,
  `commit`, `push`

Single-character / emoji that count as approve:
- `✓`, `✔`, `👍`, `+1`, `lgtm`

## Stop lexicon (case-insensitive, trimmed)

Spanish:
- `cancelar`, `cancela`, `abort`, `aborta`, `abortar`, `rollback`,
  `revierte`, `revertir`, `deshaz`, `para`, `detén`, `deten`, `stop`,
  `alto`, `no`, `rechaza`, `rechazado`

English:
- `cancel`, `abort`, `rollback`, `revert`, `undo`, `stop`, `halt`,
  `no`, `rejected`, `denied`, `scratch it`, `scrap it`, `kill it`

## Classifier algorithm (canonical order)

The reference implementation lives at `scripts/test_classifier.py`.
The algorithm in 30 lines:

```python
import re
VERB_STEMS = {
    # English
    "renam", "chang", "us", "mov", "extract", "delet", "remov",
    "add", "fix", "refactor", "split", "merg", "replac", "switch",
    "swap", "drop", "keep", "mak", "set", "put", "writ", "tri",
    "attempt", "flip", "implement", "introduc",
    # Spanish
    "cambi", "renombr", "haz", "muev", "extra", "borr", "elimin",
    "añad", "agreg", "arregl", "refactoriz", "divid", "fusion",
    "reemplaz", "sustituy", "intercambi", "manten", "escrib", "intent",
    "introduc", "quit", "pon", "met", "sac",
}
INSTRUCTION_VERBS = re.compile(
    r"\b(" + "|".join(sorted(VERB_STEMS, key=len, reverse=True)) + r")\w*\b",
    re.IGNORECASE,
)
CHANGE_QUESTION = re.compile(
    r"\?$|\b(did you|do you|why|what does|what is|is .* correct|"
    r"should we|should i|are you sure|is this|is that|really|shouldn't)\b",
    re.IGNORECASE,
)
CODE_TOKEN = re.compile(r"`[^`]+`|function\s*\(|class\s+\w+\s*:|"
                        r"\{[^}]*\}|\w+\.(py|ts|js|tsx|jsx):\d+|"
                        r"^\s*[+-]\s", re.MULTILINE)
ALTERNATIVE = re.compile(r"\binstead of\b|\brather than\b|\bwould prefer\b|"
                         r"\bprefiero\b|\bmejor con\b|\binstead\b", re.IGNORECASE)
DECLARATIVE = re.compile(r"^(the|this|we|it|esto)\s+\w+\s+(should|deber)|"
                         r"^(necesitamos|we need|hay que)\b", re.IGNORECASE)

def classify(message: str) -> str:
    msg = message.lower().strip()
    if not msg:
        return "ambiguous"
    if CHANGE_QUESTION.search(msg):         # 1. question → ambiguous
        return "ambiguous"
    if INSTRUCTION_VERBS.search(msg)        # 2. instruction → feedback
       or CODE_TOKEN.search(msg)
       or ALTERNATIVE.search(msg)
       or DECLARATIVE.search(msg):
        return "feedback"
    tokens = re.split(r"[\s,;.!¿¡:]+", msg)
    if any(t in STOP for t in tokens if t):  # 3. any stop token
        return "stop"
    if any(t in APPROVE for t in tokens if t): # 4. any approve token
        return "approve"
    if msg in APPROVE: return "approve"
    if msg in STOP:    return "stop"
    return "ambiguous"
```

**Precedence summary**: question > instruction > stop > approve > ambiguous.
Questions and instructions beat stop/approve; the agent never mistakes a
question for an order, and never mistakes a precise change request for
a generic stop.

Run `python3 scripts/test_classifier.py` to verify 30 canonical cases
(PLAN.md T6 + edge cases). The test exits non-zero if the algorithm
and the lexicons drift apart.

## Feedback detection — `looks_like_instruction(message)`

Returns `True` when the message looks like a change request. The
classifier uses **verb stems** (regex `\bstem\w*\b`) so all
conjugations match: `chang` catches change, changes, changing, changed;
`us` catches use, used, using (English) and usa, usas, usando (Spanish).

The full stem list (mirror of `scripts/test_classifier.py`):

**English (25 stems)**: renam, chang, us, mov, extract, delet, remov, add,
fix, refactor, split, merg, replac, switch, swap, drop, keep, mak, set,
put, writ, tri, attempt, flip, implement, introduc.

**Spanish (24 stems)**: cambi, renombr, haz, muev, extra, borr, elimin,
añad, agreg, arregl, refactoriz, divid, fusion, reemplaz, sustituy,
intercambi, manten, escrib, intent, introduc, quit, pon, met, sac.

Adding a stem to this list automatically catches all conjugations. If
the operator uses a verb not in this list, the feedback check still has
three other heuristics to fall back on:

3. **Code-shaped token** (any one): backticks, `function(...)`, `class X:`,
   JSON `{...}`, file path with line number (`path.ts:42`), diff
   prefix (`+` / `-` at line start).
4. **Comparison/alternative** (any one): "instead of", "rather than",
   "would prefer", "prefiero", "mejor con", "instead".
5. **Declarative start**: "the X should Y", "this should…", "we need…",
   "necesitamos…", "esto debería…".

The agent SHOULD use the full operator message history as additional
context. If the message is "ok but rename the helper", the classifier
treats it as feedback (rename is the action, "ok" is filler).

## Question detection — `looks_like_change_question(message)`

Returns `True` for questions ABOUT the change itself (vs. questions
about something else). These flag ambiguous, not feedback — a question
is not an instruction.

- ends with `?`
- AND contains: "did you", "do you", "why", "what does", "what is",
  "is X correct", "should we", "should I", "are you sure", "is this",
  "is that", "really", "shouldn't"

The agent uses the question to surface uncertainty, not to act. After
flagging ambiguous, the operator can re-respond with a clear bucket.

## Tokenization for partial matches

When a message is a phrase ("dale go", "yes go", "ok ship it"), tokenize
on whitespace + punctuation and check each token against APPROVE/STOP.
A single approve token (e.g. "dale" or "go" or "ship") is enough to
classify as approve — UNLESS the message also contains an instruction
verb or question pattern, in which case feedback/ambiguous wins.

The exact algorithm is documented above; the test cases in
`scripts/test-classifier.py` (when present) verify the precedence.

## Trigger-override words (NOT for resume classification)

The words `auto`, `autonomo`, `autónomo`, `skip-review`, `no-review`,
`without review`, `sin revisión`, `sin revisar` are TRIGGER overrides —
the operator uses them to tell the agent to skip the next pause. They
are NOT a response to an already-issued pause. If they arrive after a
pause, classify as:

- "auto" or "skip-review" arrived after a pause → **ambiguous**
  (operator may mean "skip THIS review and proceed" — close to
  approve, but the operator was supposed to be reviewing; better to
  ask). Flag with: "Detecté 'auto' después de la pausa. ¿Quieres
  saltar la review actual y proceder? Si sí, escribe 'go'."

This is a safety pattern: "auto" should be said BEFORE the agent
pauses, not after.

When classification returns `ambiguous`, the agent prints EXACTLY this
shape (no improvisation — the operator relies on the pattern):

```text
Interpreté "<original message>" como ambiguo. ¿Querías decir:
  a) aprobar y seguir (go / ok / dale)
  b) darme feedback específico
  c) abortar
?
```

…then waits. NO state change. NO classification of any sub-clause of
the message. The agent's only correct action on `ambiguous` is to ask
and wait.

## Operator can override classification

The operator can always re-classify their own message: "ignore that,
just go" overrides a feedback classification; "I said abort, not
iterate" overrides a feedback read of an ambiguous-looking word.

When the operator overrides, the agent acknowledges the override
explicitly ("OK, treating as approve") before acting. The override
becomes the canonical classification for that turn.

## Edge cases

- **Empty message** (`""` or only whitespace): treat as ambiguous.
- **Emoji-only message**: if the emoji is in the approve lexicon
  (`✓`, `👍`, `+1`), treat as approve. Otherwise ambiguous.
- **Mixed languages** ("dale go"): tokenize; any approve token wins
  when no instruction verb or question is present.
- **Quoted code** as the only content: feedback (the code IS the
  proposed change; treat as a change request).
- **Operator says "auto" before pause**: override the trigger (proceed
  without pausing). NOT a resume classification — handled separately
  in the trigger layer.
- **Operator says "auto" after pause**: ambiguous (see above).

## Anti-patterns (do NOT do)

- Classify on keyword alone. "Stop changing the file" looks like stop;
  it's actually feedback ("change it differently"). Always run the
  full classifier.
- Treat silence as approval. The agent never auto-resumes; the
  operator MUST type something.
- Treat "thanks" as approval. "Thanks, but use a different name" is
  feedback. "Thanks" alone is ambiguous.
- Treat "yes" in a question as approval. "Did you really change X?"
  answered with "yes" is not an instruction to proceed; it's
  confirmation that something happened. Re-prompt for the actual
  decision.
