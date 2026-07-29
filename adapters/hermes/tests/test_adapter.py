"""Tests for the agent-skills Hermes adapter.

Pure-function coverage of _strip_frontmatter and _build_injection. The hook
callbacks (_on_session_start, _pre_llm_call) and the register() entry
point are exercised implicitly by the same tests via the helper builders.

Run: `python -m unittest discover adapters/hermes/tests -v`
No pytest / no external deps — stdlib unittest only.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock


# --- Module loader --------------------------------------------------------

# Test file: adapters/hermes/tests/test_adapter.py
# parent.parent  = adapters/hermes/
ADAPTER_PATH = Path(__file__).resolve().parent.parent / "__init__.py"


def _load_adapter_module():
    """Import adapters/hermes/__init__.py as a module under a stable name."""
    spec = importlib.util.spec_from_file_location(
        "hermes_adapter", ADAPTER_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- _strip_frontmatter ---------------------------------------------------


class StripFrontmatterTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_adapter_module()
        self.strip = self.mod._strip_frontmatter

    def test_strips_normal_frontmatter(self):
        src = "---\nname: foo\nversion: 1.0.0\n---\n\nbody text\n"
        out = self.strip(src)
        self.assertNotIn("---", out)
        self.assertEqual(out, "body text")

    def test_no_frontmatter_returns_stripped(self):
        src = "   \njust body\n   "
        self.assertEqual(self.strip(src), "just body")

    def test_unterminated_frontmatter_returns_unchanged(self):
        src = "---\nname: foo\nstill going\n"
        # No closing \n---\n; function falls back to strip() of the
        # original content. The contract: no exception, content preserved.
        out = self.strip(src)
        self.assertIsInstance(out, str)
        # The opening --- is still there because the function didn't find
        # a closing delimiter; it just stripped whitespace from both ends.
        self.assertIn("name: foo", out)
        self.assertIn("still going", out)
        # And no exception was raised (we got here).

    def test_empty_frontmatter(self):
        src = "---\n---\nactual body\n"
        out = self.strip(src)
        self.assertEqual(out, "actual body")


# --- _resolve_bootstrap_path ----------------------------------------------


class ResolveBootstrapPathTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_adapter_module()

    def test_returns_none_when_skill_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"HERMES_HOME": tmp}):
                # Reset cached state between tests.
                self.mod._BOOTSTRAP_CACHE = None
                self.mod._BOOTSTRAP_MTIME = None
                self.assertIsNone(self.mod._resolve_bootstrap_path())

    def test_returns_path_when_skill_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "skills" / "bootstrap"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: bootstrap\n---\nbody\n")
            with mock.patch.dict(os.environ, {"HERMES_HOME": tmp}):
                self.mod._BOOTSTRAP_CACHE = None
                self.mod._BOOTSTRAP_MTIME = None
                p = self.mod._resolve_bootstrap_path()
                self.assertIsNotNone(p)
                self.assertEqual(p.name, "SKILL.md")
                self.assertEqual(p.parent.name, "bootstrap")


# --- _build_injection -----------------------------------------------------


class BuildInjectionTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_adapter_module()
        # Reset cache so each test gets a fresh load.
        self.mod._BOOTSTRAP_CACHE = None
        self.mod._BOOTSTRAP_MTIME = None

    def test_returns_none_when_bootstrap_unavailable(self):
        with mock.patch.object(self.mod, "_load_bootstrap", return_value=None):
            self.assertIsNone(self.mod._build_injection())

    def test_assembles_header_body_and_mapping(self):
        with mock.patch.object(self.mod, "_load_bootstrap", return_value="BODY-CONTENT"):
            out = self.mod._build_injection()
        self.assertIsNotNone(out)
        # Header is first.
        self.assertTrue(out.startswith(self.mod._INJECTION_HEADER))
        # Body sits in the middle.
        self.assertIn("BODY-CONTENT", out)
        # Tool mapping is last and bounded by \n\n before/after.
        self.assertTrue(out.endswith(self.mod._TOOL_MAPPING))
        # Exact three-block shape: header + \n\n + body + \n\n + mapping.
        expected = (
            f"{self.mod._INJECTION_HEADER}\n\n"
            f"BODY-CONTENT\n\n"
            f"{self.mod._TOOL_MAPPING}"
        )
        self.assertEqual(out, expected)


# --- Injection gate (_pre_llm_call) ---------------------------------------


class PreLlmCallGateTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_adapter_module()
        self.mod._BOOTSTRAP_CACHE = None
        self.mod._BOOTSTRAP_MTIME = None

    def _kwargs(self, *, is_first_turn, history):
        return dict(
            session_id="s1",
            user_message="hi",
            conversation_history=history,
            is_first_turn=is_first_turn,
            model="m",
            platform="p",
        )

    def test_injects_on_first_turn(self):
        with mock.patch.object(self.mod, "_build_injection", return_value="INJ"):
            out = self.mod._pre_llm_call(**self._kwargs(is_first_turn=True, history=[]))
        self.assertEqual(out, {"context": "INJ"})

    def test_injects_after_compaction_when_history_empty(self):
        with mock.patch.object(self.mod, "_build_injection", return_value="INJ"):
            out = self.mod._pre_llm_call(
                **self._kwargs(is_first_turn=False, history=[])
            )
        self.assertEqual(out, {"context": "INJ"})

    def test_skips_when_history_present_and_not_first_turn(self):
        with mock.patch.object(self.mod, "_build_injection", return_value="INJ"):
            out = self.mod._pre_llm_call(
                **self._kwargs(is_first_turn=False, history=["prior turn"])
            )
        self.assertIsNone(out)

    def test_returns_none_when_injection_unavailable(self):
        with mock.patch.object(self.mod, "_build_injection", return_value=None):
            out = self.mod._pre_llm_call(
                **self._kwargs(is_first_turn=True, history=[])
            )
        self.assertIsNone(out)


# --- register() entry point -----------------------------------------------


class RegisterTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_adapter_module()

    def test_registers_both_declared_hooks(self):
        class FakeCtx:
            def __init__(self):
                self.hooks = {}

            def register_hook(self, name, fn):
                self.hooks[name] = fn

        ctx = FakeCtx()
        self.mod.register(ctx)
        self.assertEqual(set(ctx.hooks.keys()), {"on_session_start", "pre_llm_call"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
