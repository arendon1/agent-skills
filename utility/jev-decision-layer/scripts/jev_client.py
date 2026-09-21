"""
JEV Decision Layer — typed-decision client.

Wraps the JEV API (TypeSafe AI System One model) with:
  * dual access route: TypeSafe direct OR Vercel AI Gateway
  * open-source alternative: Laya (Apache 2.0, 421M params) via generic HTTP
  * graceful fallback: deterministic mock when no credentials present

Three question primitives:
  - noul   (yes/no probability 0..1)
  - choice (1 of N options, N <= 255)
  - score  (ordinal 1..N)

The client never raises on missing credentials — it logs mode="fallback" and
returns a deterministic heuristic answer. Set JEV_STRICT=1 to fail fast instead.

Source: https://typesafe.ai/blog/introducing-system-one-models-and-jev
Vercel route: https://vercel.com/ai-gateway/models/jev
Laya (open alt): https://huggingface.co/convaiinnovations/laya
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Literal, Sequence

import requests

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
SKILL_DIR = Path(__file__).resolve().parent.parent
COST_LOG = SKILL_DIR / "references" / "cost-log.jsonl"
CONFIG_PATH = SKILL_DIR / "jev.json"

# Default endpoints
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
VERCEL_AIGATEWAY_URL = "https://ai-gateway.vercel.sh/v1/evaluate"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Pricing ($/1M tokens). Output is FREE for all known System One models.
PRICE_INPUT_USD_PER_1M = 0.042  # TypeSafe direct
PRICE_VERCEL_USD_PER_1M = 0.04  # Vercel AIGateway (may vary slightly)
# OpenRouter is an LLM with a JSON-schema response format — billed both ways.
# Defaults match deepseek-v4-flash-0731 ("v4-text"), our cheapest authorized lane.
PRICE_OPENROUTER_IN_PER_1M = 0.065
PRICE_OPENROUTER_OUT_PER_1M = 0.18
# Laya is self-hosted; compute cost is operator's problem.

# Per-question cap (TypeSafe). Below this, single pass; above, 2-stage scoring.
CARDINALITY_2STAGE = 50

DEFAULT_TIMEOUT_S = 12.0

# --------------------------------------------------------------------------- #
# Types
# --------------------------------------------------------------------------- #
QuestionType = Literal["noul", "choice", "score"]


@dataclass
class Question:
    key: str
    type: QuestionType
    instructions: str
    options: list[str] | None = None  # required for "choice"
    range_max: int | None = None  # required for "score" (1..range_max)


@dataclass
class Answer:
    key: str
    type: QuestionType
    value: float | int | str  # noul in [0,1], score int, choice str
    probability: float | None = None  # calibrated, only when choice/score

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Verdict:
    answers: dict[str, Answer] = field(default_factory=dict)
    mode: Literal["live", "vercel", "laya", "openrouter", "fallback", "error"] = "fallback"
    cost_usd: float = 0.0
    latency_ms: int = 0
    tokens_in: int = 0
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    error: str | None = None
    raw: dict | None = None

    def __getitem__(self, key: str) -> Answer:
        return self.answers[key]

    def items(self):
        return self.answers.items()

    def as_dict(self) -> dict:
        return {
            "answers": {k: a.as_dict() for k, a in self.answers.items()},
            "mode": self.mode,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "tokens_in": self.tokens_in,
            "request_id": self.request_id,
            "error": self.error,
        }


# --------------------------------------------------------------------------- #
# Configuration loading (mirror openrouter.json pattern)
# --------------------------------------------------------------------------- #
def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class JEV:
    """Thin wrapper around a System One model (JEV / Laya / fallback).

    Parameters
    ----------
    backend : optional str
        Force one of: "vercel" | "typesafe" | "laya" | "fallback".
        If not given, picks first available from env.
    base_url : optional str
        Override the endpoint URL (e.g. for self-hosted Laya or a proxy).
    api_key : optional str
        Override credentials lookup.
    timeout : float
        HTTP request timeout in seconds.
    strict : bool
        If True, missing-credentials raises instead of falling back.
    """

    _SCHEMA = {
        "type": "object",
        "properties": {
            "model": {"type": "string"},
            "state": {"type": ["string", "object", "array"]},
            "questions": {"type": "object"},
        },
        "required": ["state", "questions"],
    }

    def __init__(
        self,
        backend: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_S,
        strict: bool | None = None,
    ) -> None:
        cfg = _load_config()
        api_cfg = cfg.get("api", {})

        self.timeout = float(os.environ.get("JEV_TIMEOUT", api_cfg.get("timeout", timeout)))
        self.strict = (
            strict
            if strict is not None
            else bool(int(os.environ.get("JEV_STRICT", "0")))
        )

        # Resolve backend (priority: explicit > env > detection > fallback)
        chosen = (
            backend
            or os.environ.get("JEV_BACKEND")
            or self._auto_detect(api_key=api_key, base_url=base_url)
        )

        # Strict mode: refuse to silently fall back when no explicit backend was given
        if self.strict and not backend and chosen == "fallback":
            raise RuntimeError(
                "JEV_STRICT=1 but no backend credentials configured "
                "(set TYPESAFE_API_KEY, VERCEL_API_KEY, or JEV_BASE_URL)"
            )

        # Per-backend credentials and endpoint
        if chosen == "openrouter":
            self.mode: Literal["live", "vercel", "laya", "openrouter", "fallback", "error"] = "openrouter"
            self.base_url = base_url or os.environ.get(
                "JEV_BASE_URL", cfg.get("endpoints", {}).get("openrouter", OPENROUTER_URL)
            )
            self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
            self.model = cfg.get("openrouter_model", "deepseek/deepseek-v4-flash-0731")
            self.price_per_1m = PRICE_OPENROUTER_IN_PER_1M
            self.price_out_per_1m = PRICE_OPENROUTER_OUT_PER_1M
            self.reasoning_enabled = bool(
                int(os.environ.get("JEV_OPENROUTER_REASONING", "0"))
            )
        elif chosen == "vercel":
            self.mode = "vercel"
            self.base_url = base_url or os.environ.get(
                "JEV_BASE_URL", cfg.get("endpoints", {}).get("vercel", VERCEL_AIGATEWAY_URL)
            )
            self.api_key = api_key or os.environ.get("VERCEL_API_KEY") or os.environ.get(
                "AI_GATEWAY_API_KEY"
            )
            self.model = cfg.get("default_model", "typesafe-ai/jev")
            self.price_per_1m = PRICE_VERCEL_USD_PER_1M
            self.price_out_per_1m = 0.0
        elif chosen == "typesafe":
            self.mode = "live"
            self.base_url = base_url or os.environ.get(
                "JEV_BASE_URL", cfg.get("endpoints", {}).get("typesafe", TYPESAFE_URL)
            )
            self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
            self.model = cfg.get("default_model", "jev-latest")
            self.price_per_1m = PRICE_INPUT_USD_PER_1M
            self.price_out_per_1m = 0.0
        elif chosen == "laya":
            self.mode = "laya"
            self.base_url = base_url or os.environ.get(
                "JEV_BASE_URL", cfg.get("endpoints", {}).get("laya", "http://localhost:8000")
            )
            self.api_key = api_key or os.environ.get("LAYA_API_KEY", "")
            self.model = cfg.get("default_model", "laya-decision")
            self.price_per_1m = 0.0
            self.price_out_per_1m = 0.0
        elif chosen == "fallback":
            self.mode = "fallback"
            self.base_url = ""
            self.api_key = ""
            self.model = "fallback-heuristic"
            self.price_per_1m = 0.0
            self.price_out_per_1m = 0.0
        else:
            # Unknown → safe fallback
            if self.strict:
                raise RuntimeError(f"JEV: unknown backend '{chosen}' (strict mode)")
            self.mode = "fallback"
            self.base_url = ""
            self.api_key = ""
            self.model = "fallback-heuristic"
            self.price_per_1m = 0.0
            self.price_out_per_1m = 0.0

        # Auto-degrade fallback if creds missing in non-fallback mode
        if self.mode != "fallback" and not self.api_key and not self.base_url.startswith("http"):
            if self.strict:
                raise RuntimeError(
                    f"JEV: backend={chosen} but no credentials (set API key or JEV_STRICT=0)"
                )
            self.mode = "fallback"
            self.base_url = ""
            self.api_key = ""

    # ------------------------------------------------------------------ #
    # Detection
    # ------------------------------------------------------------------ #
    def _auto_detect(self, api_key: str | None = None, base_url: str | None = None) -> str:
        # Local Laya first (no egress at all if it's running)
        if os.environ.get("JEV_BASE_URL", "").startswith("http://localhost") or base_url:
            return "laya"
        if os.environ.get("LAYA_API_KEY"):
            return "laya"
        # Then the already-authorized egress host (OpenRouter is Tier-1 allowlisted).
        if os.environ.get("OPENROUTER_API_KEY"):
            return "openrouter"
        # New-egress routes: only when explicitly keyed.
        if os.environ.get("VERCEL_API_KEY") or os.environ.get("AI_GATEWAY_API_KEY") or api_key:
            return "vercel"
        if os.environ.get("TYPESAFE_API_KEY"):
            return "typesafe"
        return "fallback"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def classify(
        self,
        state: str | dict | list,
        questions: dict[str, tuple[QuestionType, str]] | Sequence[Question] | dict[str, dict],
    ) -> Verdict:
        """Run a decision call.

        Parameters
        ----------
        state : str|dict|list
            The "state" the questions are evaluated against. Strings are
            passed through; dict/list are JSON-serialized.
        questions : varies
            Either:
              * dict of {key: (type, instructions)} tuples (sugar)
              * dict of {key: {type: ..., instructions: ..., options?: [...], range_max?: int}}
              * list of Question objects
        """
        # Normalize questions
        normalized = self._normalize_questions(questions)

        if self.mode == "fallback":
            return self._fallback_call(state, normalized)
        if self.mode == "laya":
            return self._http_call_laya(state, normalized)
        if self.mode == "openrouter":
            return self._http_call_openrouter(state, normalized)
        if self.mode in ("live", "vercel"):
            return self._http_call(state, normalized)

        return Verdict(error=f"unknown mode: {self.mode}")

    # ------------------------------------------------------------------ #
    # Question normalization
    # ------------------------------------------------------------------ #
    def _normalize_questions(self, questions) -> dict[str, dict]:
        if isinstance(questions, dict) and questions and isinstance(next(iter(questions.values())), tuple):
            # sugar: dict[key] = (type, instructions)
            out = {}
            for k, v in questions.items():
                t, instr = v[0], v[1]
                opts = v[2] if len(v) > 2 else None
                rng = v[3] if len(v) > 3 else None
                out[k] = self._normalize_one(k, t, instr, opts, rng)
            return out
        if isinstance(questions, dict):
            out = {}
            for k, v in questions.items():
                if isinstance(v, dict):
                    out[k] = self._normalize_one(
                        k,
                        v.get("type", "noul"),
                        v.get("instructions", ""),
                        v.get("options"),
                        v.get("range_max"),
                    )
                else:
                    raise ValueError(f"question[{k}]: expected dict, got {type(v)}")
            return out
        # Sequence[Question]
        out = {}
        for q in questions:
            out[q.key] = self._normalize_one(q.key, q.type, q.instructions, q.options, q.range_max)
        return out

    def _normalize_one(self, key, type_, instr, opts, rng) -> dict:
        if type_ not in ("noul", "choice", "score"):
            raise ValueError(f"question[{key}]: unknown type '{type_}'")
        q = {"type": type_, "instructions": instr}
        if type_ == "choice":
            if not opts:
                raise ValueError(f"question[{key}] (choice): options required")
            if len(opts) > 255:
                raise ValueError(f"question[{key}] (choice): max 255 options")
            q["options"] = list(opts)
        elif type_ == "score":
            # In tuple sugar, slot 3 maps to range_max for score
            actual_rng = rng if rng is not None else opts
            if actual_rng is None or actual_rng < 2:
                raise ValueError(f"question[{key}] (score): range_max required (>=2)")
            q["range_max"] = int(actual_rng)
        return q

    # ------------------------------------------------------------------ #
    # HTTP: JEV / Vercel Gateway
    # ------------------------------------------------------------------ #
    def _http_call(self, state, questions) -> Verdict:
        body: dict[str, Any] = {
            "model": self.model,
            "state": state,
            "questions": {k: {"type": v["type"], "instructions": v["instructions"]}
                          for k, v in questions.items()},
        }
        # Add options for choice, range for score
        for k, v in questions.items():
            if v["type"] == "choice":
                body["questions"][k]["options"] = v["options"]
            elif v["type"] == "score":
                body["questions"][k]["range"] = [1, v["range_max"]]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        t0 = time.time()
        try:
            r = requests.post(self.base_url, json=body, headers=headers, timeout=self.timeout)
            latency_ms = int((time.time() - t0) * 1000)
            if r.status_code != 200:
                if self.strict:
                    raise RuntimeError(f"JEV HTTP {r.status_code}: {r.text[:300]}")
                # silent fallback, log it
                v = self._fallback_call(state, questions, reason=f"http {r.status_code}")
                v.latency_ms = latency_ms
                return v
            data = r.json()
        except requests.RequestException as e:
            if self.strict:
                raise RuntimeError(f"JEV unreachable: {e}") from e
            v = self._fallback_call(state, questions, reason=str(e)[:200])
            v.latency_ms = int((time.time() - t0) * 1000)
            return v

        tokens_in = self._estimate_tokens(state) + sum(
            self._estimate_tokens(str(v)) for v in questions.values()
        )
        verdict = self._parse_response(questions, data)
        verdict.mode = self.mode
        verdict.tokens_in = tokens_in
        verdict.cost_usd = tokens_in / 1_000_000 * self.price_per_1m
        verdict.latency_ms = latency_ms
        verdict.raw = data
        self._log(verdict)
        return verdict

    # ------------------------------------------------------------------ #
    # HTTP: Laya (open-source, expected to mimic JEV schema)
    # ------------------------------------------------------------------ #
    def _http_call_laya(self, state, questions) -> Verdict:
        # Laya exposes a JEV-compatible endpoint at <base>/classify or /v1/systemone
        url = self.base_url.rstrip("/") + "/v1/systemone"
        body = {
            "state": state,
            "questions": {
                k: {"type": v["type"], "instructions": v["instructions"]}
                | ({"options": v["options"]} if v["type"] == "choice" else {})
                | ({"range": [1, v["range_max"]]} if v["type"] == "score" else {})
                for k, v in questions.items()
            },
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        t0 = time.time()
        try:
            r = requests.post(url, json=body, headers=headers, timeout=self.timeout)
            latency_ms = int((time.time() - t0) * 1000)
            if r.status_code != 200:
                if self.strict:
                    raise RuntimeError(f"Laya HTTP {r.status_code}: {r.text[:300]}")
                v = self._fallback_call(state, questions, reason=f"http {r.status_code}")
                v.latency_ms = latency_ms
                return v
            data = r.json()
        except requests.RequestException as e:
            if self.strict:
                raise RuntimeError(f"Laya unreachable: {e}") from e
            v = self._fallback_call(state, questions, reason=str(e)[:200])
            v.latency_ms = int((time.time() - t0) * 1000)
            return v

        tokens_in = self._estimate_tokens(state)
        verdict = self._parse_response(questions, data)
        verdict.mode = "laya"
        verdict.tokens_in = tokens_in
        verdict.cost_usd = 0.0  # self-hosted compute is out-of-band
        verdict.latency_ms = latency_ms
        verdict.raw = data
        self._log(verdict)
        return verdict

    def _http_call_openrouter(self, state, questions) -> Verdict:
        """Route decisions through an OpenRouter chat model with a JSON-schema
        response format.

        IMPORTANT — this is NOT a System One model. It is an ordinary LLM
        constrained to emit a typed object. Consequences versus JEV/Laya:

          * `noul` probabilities are heuristic, NOT calibrated. Treat them as
            a soft signal, not a probability you can threshold on.
          * The schema shape is guaranteed by `response_format` (strict), but
            the model can still be *wrong* about the substance.
          * Cost is per input AND output token (unlike JEV, whose output is free).

        What it buys: it rides an egress host already authorized for this box,
        on a lane already paid for — no new vendor, no new host.
        """
        if isinstance(state, (dict, list)):
            state = json.dumps(state, ensure_ascii=False, default=str)

        # Build the response JSON schema from the questions
        props: dict[str, Any] = {}
        specs: list[str] = []
        for k, q in questions.items():
            if q["type"] == "noul":
                props[k] = {"type": "number", "minimum": 0, "maximum": 1}
                specs.append(f'- "{k}": {q["instructions"]} → a probability in [0,1]')
            elif q["type"] == "choice":
                props[k] = {"type": "string", "enum": q["options"]}
                specs.append(f'- "{k}": {q["instructions"]} → one of: {", ".join(q["options"])}')
            elif q["type"] == "score":
                props[k] = {"type": "integer", "minimum": 1, "maximum": q["range_max"]}
                specs.append(f'- "{k}": {q["instructions"]} → an integer from 1 to {q["range_max"]}')

        schema = {
            "name": "typed_decisions",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": props,
                "required": list(props),
                "additionalProperties": False,
            },
        }

        system = (
            "You are a strict decision classifier. Given a STATE and typed QUESTIONS, "
            "answer each question about the state. Output ONLY JSON matching the schema. "
            "For yes/no questions output a probability: near 0.5 when the state is "
            "ambiguous, near 0 or 1 when unambiguous. Pick exactly one allowed option. "
            "Never explain."
        )
        user = "STATE:\n" + str(state)[:20000] + "\n\nQUESTIONS:\n" + "\n".join(specs)

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_schema", "json_schema": schema},
            "temperature": 0,
            # Reasoning off is load-bearing: measured 5.9s -> 1.6s and output
            # tokens 108 -> 11 on v4-text. A classifier does not need a chain
            # of thought; it needs a bounded decision.
            "reasoning": {"enabled": self.reasoning_enabled},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        t0 = time.time()
        try:
            r = requests.post(self.base_url, json=body, headers=headers, timeout=self.timeout)
            latency_ms = int((time.time() - t0) * 1000)
            if r.status_code != 200:
                if self.strict:
                    raise RuntimeError(f"OpenRouter HTTP {r.status_code}: {r.text[:300]}")
                v = self._fallback_call(state, questions, reason=f"http {r.status_code}")
                v.latency_ms = latency_ms
                return v
            data = r.json()
        except requests.RequestException as e:
            if self.strict:
                raise RuntimeError(f"OpenRouter unreachable: {e}") from e
            v = self._fallback_call(state, questions, reason=str(e)[:200])
            v.latency_ms = int((time.time() - t0) * 1000)
            return v

        try:
            content = data["choices"][0]["message"]["content"]
            raw = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            if self.strict:
                raise RuntimeError(f"OpenRouter malformed response: {e}") from e
            v = self._fallback_call(state, questions, reason="malformed")
            v.latency_ms = latency_ms
            return v

        ans: dict[str, Answer] = {}
        for k, q in questions.items():
            val = raw.get(k)
            if q["type"] == "noul":
                try:
                    fval = max(0.0, min(1.0, float(val)))
                except (TypeError, ValueError):
                    fval = 0.5
                ans[k] = Answer(key=k, type="noul", value=fval, probability=fval)
            elif q["type"] == "choice":
                sval = str(val)
                if sval not in q["options"]:
                    sval = q["options"][0]
                ans[k] = Answer(key=k, type="choice", value=sval, probability=None)
            elif q["type"] == "score":
                try:
                    ival = int(val)
                except (TypeError, ValueError):
                    ival = 1
                ival = max(1, min(q["range_max"], ival))
                ans[k] = Answer(key=k, type="score", value=ival, probability=None)

        usage = data.get("usage") or {}
        tokens_in = usage.get("prompt_tokens") or self._estimate_tokens(state)
        tokens_out = usage.get("completion_tokens") or 30

        verdict = Verdict(answers=ans, mode="openrouter")
        verdict.tokens_in = tokens_in
        verdict.cost_usd = (
            tokens_in / 1_000_000 * self.price_per_1m
            + tokens_out / 1_000_000 * getattr(self, "price_out_per_1m", 0.0)
        )
        verdict.latency_ms = latency_ms
        verdict.raw = data
        self._log(verdict)
        return verdict

    # ------------------------------------------------------------------ #
    # Fallback (deterministic heuristic)
    # ------------------------------------------------------------------ #
    def _fallback_call(self, state, questions, reason: str | None = None) -> Verdict:
        """Return deterministic placeholder answers.

        Strategy: hash(state+instructions+key); pick a value in [0.4, 0.95] for noul;
        first option for choice; midpoint for score. This gives reproducible results
        across calls (useful for testing) and never raises.
        """
        sid = str(state)
        ans: dict[str, Answer] = {}
        for k, v in questions.items():
            t = v["type"]
            if t == "noul":
                h = int(hashlib.md5((sid + k).encode()).hexdigest()[:8], 16)
                val = 0.4 + (h % 55) / 100.0  # 0.40..0.95
                ans[k] = Answer(key=k, type=t, value=val, probability=val)
            elif t == "choice":
                opts = v["options"]
                ans[k] = Answer(key=k, type=t, value=opts[0], probability=0.5)
            elif t == "score":
                rng = v["range_max"]
                mid = max(1, rng // 2)
                ans[k] = Answer(key=k, type=t, value=mid, probability=0.5)
        v = Verdict(answers=ans, mode="fallback", cost_usd=0.0, tokens_in=0, latency_ms=0)
        if reason:
            v.error = f"fallback_reason:{reason}"
        # Log fallback too — keeps the ledger honest
        self._log(v)
        return v

    # ------------------------------------------------------------------ #
    # Parsing
    # ------------------------------------------------------------------ #
    def _parse_response(self, questions, data) -> Verdict:
        ans: dict[str, Answer] = {}
        # Expected: {"question_key": {"type": ..., "noul"|"choice"|"score": value, "probabilities"?: {...}}}
        if not isinstance(data, dict):
            return Verdict(error=f"non-dict response: {type(data)}")
        # El wrapper HTTP de Laya anida las respuestas bajo "answers"; la API de
        # TypeSafe las trae al nivel raiz. Aceptamos ambas formas.
        if isinstance(data.get("answers"), dict):
            data = data["answers"]
        for k, v in questions.items():
            payload = data.get(k) or {}
            if not isinstance(payload, dict):
                ans[k] = Answer(key=k, type=v["type"], value=0, probability=None)
                continue
            t = payload.get("type", v["type"])
            if t == "noul":
                val = float(payload.get("noul", payload.get("value", 0)))
                ans[k] = Answer(key=k, type=t, value=val, probability=val)
            elif t == "choice":
                val = payload.get("choice", payload.get("value", ""))
                prob = payload.get("probabilities") or {}
                pval = None
                if isinstance(prob, dict) and val in prob:
                    try:
                        pval = float(prob[val])
                    except (TypeError, ValueError):
                        pval = None
                ans[k] = Answer(key=k, type=t, value=val, probability=pval)
            elif t == "score":
                val = int(payload.get("score", payload.get("value", 1)))
                ans[k] = Answer(key=k, type=t, value=val, probability=None)
            else:
                ans[k] = Answer(key=k, type=t, value=payload.get("value", 0), probability=None)
        return Verdict(answers=ans)

    # ------------------------------------------------------------------ #
    # Token estimation (rough — assumes 1 token ~ 4 chars)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _estimate_tokens(s) -> int:
        if isinstance(s, (dict, list)):
            s = json.dumps(s, separators=(",", ":"))
        s = str(s)
        return max(1, len(s) // 4)

    # ------------------------------------------------------------------ #
    # Cost ledger
    # ------------------------------------------------------------------ #
    def _log(self, verdict: Verdict) -> None:
        COST_LOG.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "request_id": verdict.request_id,
                "mode": verdict.mode,
                "model": self.model,
                "tokens_in": verdict.tokens_in,
                "cost_usd": verdict.cost_usd,
                "latency_ms": verdict.latency_ms,
                "questions": len(verdict.answers),
                "error": verdict.error,
            },
            separators=(",", ":"),
        )
        with COST_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


# --------------------------------------------------------------------------- #
# CLI convenience (lightweight)
# --------------------------------------------------------------------------- #
def _main(argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(description="JEV classify (CLI)")
    sub = p.add_subparsers(dest="cmd")
    pc = sub.add_parser("classify")
    pc.add_argument("--state", required=True)
    pc.add_argument("--backend")
    pc.add_argument("--preset")
    pc.add_argument("--question", action="append", default=[],
                   help='key="type:instructions". Repeatable.')
    pc.add_argument("--json", action="store_true")

    args = p.parse_args(argv)

    if args.cmd != "classify":
        p.print_help()
        return 2

    # Try to import presets if --preset given
    questions = {}
    if args.preset:
        try:
            from jev_schemas import PRESETS
            preset = PRESETS.get(args.preset)
            if not preset:
                raise ValueError(f"unknown preset: {args.preset}")
            for k, v in preset.items():
                questions[k] = (v["type"], v["instructions"])
        except ImportError:
            print("ERROR: --preset requires jev_schemas.py on path", file=sys.stderr)
            return 3

    # Inline questions override preset
    for q in args.question:
        if "=" not in q:
            continue
        k, payload = q.split("=", 1)
        if ":" not in payload:
            continue
        t, instr = payload.split(":", 1)
        t = t.strip().strip('"')
        instr = instr.strip().strip('"')
        questions[k.strip()] = (t, instr)

    client = JEV(backend=args.backend)
    verdict = client.classify(args.state, questions)
    if args.json:
        print(json.dumps(verdict.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(verdict.as_dict(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
