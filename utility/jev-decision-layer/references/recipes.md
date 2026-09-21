# Recipes — JEV Decision Layer per scenario

How each of the 6 identified scenarios wires up against this skill.

## Recipe 0 — The "must not crash" guarantee

Every recipe below works in 3 modes:

| Mode | Trigger | Behavior |
|---|---|---|
| `live` / `vercel` | API key set | Real JEV call, $0.04/1M tokens, ~250ms latency |
| `laya` | `JEV_BASE_URL` set | Self-hosted open-source, free, ~30ms |
| `fallback` | Nothing set | Deterministic heuristic, instant, free |

The caller never has to branch on mode. The verdict carries `mode` so you can
audit which mode served each call.

## Recipe 1 — H5P solver guardarraíl (slide "did this score max?")

```python
from jev_client import JEV
from jev_schemas import SLIDE_DONE_V1

client = JEV()
state = serialize_slide_state(slide_dom)  # your existing serialization
verdict = client.classify(state, SLIDE_DONE_V1)

if (verdict["score_at_max"].value < 0.95
    or verdict["all_answers_committed"].value < 0.95):
    retry_or_flag(slide)
```

CLI equivalent:
```bash
python jev_cli.py classify \
  --state "$(serialize_slide slide_123)" \
  --preset slide_done_v1
```

## Recipe 2 — FindTheWords drag safety

```python
verdict = client.classify(canvas_state, FIND_WORDS_DRAG_V1)
safe = all(v.value >= 0.95 for k, v in verdict.items()
           if k in ("start_in_viewport", "end_in_viewport"))
uninterrupted = verdict["path_uninterrupted"].value >= 0.90
if safe and uninterrupted:
    emit_drag(start, end)
```

## Recipe 3 — Course completion check

```python
verdict = client.classify(grade_report_html, COURSE_CLOSED_V1)
closed = (
    verdict["todos_al_100"].value >= 0.95
    and verdict["faltan_intentados"].value < 0.50
    and verdict["hay_nota_baja"].value < 0.50
    and verdict["rumbo_coherente"].value >= 4
)
if closed:
    mark_course_closed(course_id)
```

## Recipe 4 — HyperFrames render quality gate

```python
verdict = client.classify(render_metadata, RENDER_GATE_V1)
choice = verdict["render_succeeded"].value
glitch = verdict["no_visual_glitches"].value
if choice == "pass" and glitch >= 0.90:
    auto_publish(render)
elif choice == "needs_re_render" and verdict["render_succeeded"].probability >= 0.85:
    re_render(seed=seed + 1)
else:
    queue_for_human_review()
```

## Recipe 5 — ai-check multi-dimension scoring

```python
verdict = client.classify(document_text, AI_DIMENSIONS_V1)
composite = score(
    em_dash=verdict["has_em_dash_overuse"].value,
    banned=verdict["uses_banned_vocab"].value,
    uniform=verdict["uniform_sentence_len"].value,
    template=verdict["templated_structure"].value,
    voice=verdict["voice_consistency"].value,
    human=verdict["human_likelihood"].value,
)
report = {
    "dimensions": verdict.as_dict()["answers"],
    "composite_score": composite,
    "mode": verdict.mode,
    "cost_usd": verdict.cost_usd,
}
```

## Recipe 6 — agy output triage

```python
research = await agy_delegate(prompt)
verdict = client.classify(research.text, TRIAGE_QUALITY_V1)
if (verdict["answer_addresses_question"].value < 0.6
    or verdict["needs_followup"].value == "yes_urgent"):
    await agy_followup(original_prompt, gap=verdict.summary)
```

## Subprocess wrapper for cross-skill use (§12)

When calling from another skill (e.g. `gestionar-cursos`), use:

```python
import subprocess, json

result = subprocess.run(
    ["python", "<jev-decision-layer>/scripts/jev_cli.py", "classify",
     "--state", str(state),
     "--preset", "slide_done_v1"],
    capture_output=True, text=True, check=True,
)
verdict = json.loads(result.stdout)
```

This satisfies §12 (no code imports across skills).
