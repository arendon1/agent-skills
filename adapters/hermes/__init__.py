"""agent-skills Hermes adapter (Layer 4).

The ONLY place harness-specific coupling lives for Hermes. Skills express
behavior in agnostic terms; this adapter maps those behaviors to Hermes's
concrete tools. It mirrors the pi adapter (.pi/extensions/agent-skills.ts)
using Hermes's plugin hook system.

Three responsibilities (same as pi):
  1. Skill discovery — Hermes handles natively (skills_list / skill_view).
     No adapter action needed.
  2. Bootstrap injection — pre_llm_call injects the bootstrap skill body +
     Hermes tool mapping into the first turn of every new session, and
     re-injects after context compaction (when Hermes rebuilds the system
     prompt with an empty conversation history). No session-id tracking
     is needed: the (is_first_turn, conversation_history) pair the hook
     receives is the ground truth.
  3. Tool mapping — a static block appended to the bootstrap injection that
     maps agnostic skill behaviors to Hermes's named tools.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# --- Bootstrap skill resolution -------------------------------------------

# The bootstrap skill is installed at ~/.hermes/skills/bootstrap/SKILL.md
# (produced by `npx skills add .`). We resolve it at injection time so
# the adapter survives skill re-installs.
_BOOTSTRAP_CACHE: Optional[str] = None
_BOOTSTRAP_MTIME: Optional[float] = None


def _hermes_home() -> Path:
    """Return the active HERMES_HOME, honouring the env var."""
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def _resolve_bootstrap_path() -> Optional[Path]:
    """Find the bootstrap SKILL.md under the active Hermes home.

    Canonical install path produced by `npx skills add .` (Hermes
    discovers skills at ~/.hermes/skills/<name>/SKILL.md). HERMES_HOME
    is honoured for hermetic test setups.
    """
    path = _hermes_home() / "skills" / "bootstrap" / "SKILL.md"
    if path.exists():
        return path
    logger.debug("agent-skills adapter: bootstrap SKILL.md not found at %s", path)
    return None


def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from a SKILL.md body.

    The closing boundary is unambiguously marked by a leading newline
    (`\n---\n`), so we search from index 0 — the opening `---\n` does not
    itself contain a leading newline and cannot be confused for the close.
    """
    if content.startswith("---\n"):
        end = content.find("\n---\n")
        if end != -1:
            return content[end + 5 :].strip()
    return content.strip()


def _load_bootstrap() -> Optional[str]:
    """Load and cache the bootstrap skill body, re-reading on file change."""
    global _BOOTSTRAP_CACHE, _BOOTSTRAP_MTIME

    path = _resolve_bootstrap_path()
    if path is None:
        return None

    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None

    if _BOOTSTRAP_CACHE is not None and mtime == _BOOTSTRAP_MTIME:
        return _BOOTSTRAP_CACHE

    try:
        raw = path.read_text(encoding="utf-8")
        _BOOTSTRAP_CACHE = _strip_frontmatter(raw)
        _BOOTSTRAP_MTIME = mtime
        logger.debug("agent-skills adapter: loaded bootstrap (%d chars)", len(_BOOTSTRAP_CACHE))
    except OSError as e:
        logger.warning("agent-skills adapter: could not read %s: %s", path, e)
        return None

    return _BOOTSTRAP_CACHE


# --- Hermes tool mapping --------------------------------------------------

# The behavior -> tool mapping. This is the ONLY place Hermes-specific tool
# names appear in the agent-skills system; skills themselves never name them
# (AGENTS.md §9 agnosticism).

_TOOL_MAPPING = """\
## Hermes tool mapping

agent-skills express behavior in harness-agnostic terms. This adapter maps \
those behaviors to Hermes's concrete tools for this session.

**Load a skill:** Hermes has native skill tools. When a skill says to "load \
a skill" or "invoke the X skill", use `skill_view(name)` to load it, or \
`skills_list` to discover available skills. Do not invent a separate skill \
loader.

**Dispatch a subagent:** Use `delegate_task(goal, context)` for subagent \
workflows (the dispatch skill). For batches, pass `tasks=[...]` to run \
children in parallel. For long-lived work, use `terminal(background=True, \
notify_on_complete=True)` instead.

**Track a task:** Use the `todo` tool to create and update task items. \
Alternatively, track work in the active plan's PLAN.md task status cells \
(build flips `[ ]` -> `~` -> `[x]`).

**Read / write / edit files:** Use `read_file` (not cat), `write_file` \
(not echo/cat heredoc), `patch` (not sed/awk), and `search_files` (not \
grep/rg/find).

**Run shell commands:** Use `terminal`. For long-running commands, set \
`background=True` with `notify_on_complete=True`.

**Search the web:** Use `web_search` and `web_extract`.

**Recall long-term memory:** Use the `memory` tool. Project artifacts \
(CONTEXT.md, docs/plans/) are externalized state, not memory — check and \
update them per the bootstrap skill's Habit 2.
"""


# --- Injection content ----------------------------------------------------

_INJECTION_HEADER = (
    "agent-skills:bootstrap injection for Hermes\n\n"
    "You have agent-skills.\n\n"
    "The bootstrap skill content is included below and is already loaded for "
    "this Hermes session. Follow it now. Do not try to load bootstrap again — "
    "it is active."
)


def _build_injection() -> Optional[str]:
    """Assemble the full bootstrap injection (header + body + tool mapping)."""
    body = _load_bootstrap()
    if body is None:
        return None
    return f"{_INJECTION_HEADER}\n\n{body}\n\n{_TOOL_MAPPING}"


# --- Plugin registration --------------------------------------------------

# pre_llm_call fires on every turn, but the bootstrap only needs to land
# once: at the start of a new session, and again after context compaction
# (when Hermes rebuilds the system prompt with an empty conversation
# history). We detect both with the (is_first_turn, conversation_history)
# pair that Hermes passes in — no need for a session-id set, which would
# be a stale data hazard on restart.


def _on_session_start(session_id: str, **kwargs: Any) -> None:
    """Log session start. No state to reset; the injection gate uses
    is_first_turn + history emptiness, not a session-id set."""
    logger.debug("agent-skills adapter: session_start %s", session_id)


def _pre_llm_call(
    session_id: str,
    user_message: str,
    conversation_history: list,
    is_first_turn: bool,
    model: str,
    platform: str,
    **kwargs: Any,
) -> Optional[dict]:
    """Inject bootstrap on the first turn of a new session.

    Also re-injects after compaction: if the conversation history is empty
    (which happens both on genuinely new sessions and after compaction),
    inject. This mirrors the pi adapter's session_compact behaviour without
    needing a dedicated hook.
    """
    injection = _build_injection()
    if injection is None:
        return None

    # Inject on first turn, or when history is empty (post-compaction).
    # The is_first_turn flag covers genuinely new sessions; the empty
    # conversation_history check covers compaction (the system prompt is
    # rebuilt but history is wiped).
    if is_first_turn or not conversation_history:
        logger.debug(
            "agent-skills adapter: injecting bootstrap for session %s "
            "(first_turn=%s, history_empty=%s)",
            session_id,
            is_first_turn,
            not conversation_history,
        )
        return {"context": injection}

    return None


def register(ctx):
    """Plugin entry point — register hooks with Hermes."""
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    logger.info("agent-skills adapter registered (pre_llm_call + on_session_start)")
