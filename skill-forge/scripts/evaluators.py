"""Abstract base class and implementations for agent evaluators.

Each evaluator provides a way to check if a specific AI agent (CLIs or APIs)
is triggered by a given skill description for a specific query.
"""

import abc
import json
import os
import subprocess
import sys
import time
import uuid
import select
from pathlib import Path
from typing import Optional, Dict, Any


class BaseEvaluator(abc.ABC):
    """Base class for all evaluators."""

    @abc.abstractmethod
    def run_query(
        self,
        query: str,
        skill_name: str,
        skill_description: str,
        timeout: int,
        project_root: str,
        model: Optional[str] = None,
    ) -> bool:
        """Run a single query and return true if the skill was triggered."""
        pass

    @abc.abstractmethod
    def cleanup(self):
        """Clean up any temporary files or processes."""
        pass


class ClaudeCodeEvaluator(BaseEvaluator):
    """Evaluator for Anthropic's Claude Code CLI."""

    def __init__(self):
        self.temp_command_file: Optional[Path] = None

    def run_query(
        self,
        query: str,
        skill_name: str,
        skill_description: str,
        timeout: int,
        project_root: str,
        model: Optional[str] = None,
    ) -> bool:
        unique_id = uuid.uuid4().hex[:8]
        clean_name = f"{skill_name}-skill-{unique_id}"
        project_commands_dir = Path(project_root) / ".claude" / "commands"
        self.temp_command_file = project_commands_dir / f"{clean_name}.md"

        try:
            project_commands_dir.mkdir(parents=True, exist_ok=True)
            indented_desc = "\n  ".join(skill_description.split("\n"))
            command_content = (
                f"---\n"
                f"description: |\n"
                f"  {indented_desc}\n"
                f"---\n\n"
                f"# {skill_name}\n\n"
                f"This skill handles: {skill_description}\n"
            )
            self.temp_command_file.write_text(command_content, encoding="utf-8")

            cmd = [
                "claude",
                "-p",
                query,
                "--output-format",
                "stream-json",
                "--verbose",
                "--include-partial-messages",
            ]
            if model:
                cmd.extend(["--model", model])

            env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=project_root,
                env=env,
            )

            triggered = False
            start_time = time.time()
            buffer = ""
            pending_tool_name = None
            accumulated_json = ""

            try:
                while time.time() - start_time < timeout:
                    if process.poll() is not None:
                        remaining = process.stdout.read()
                        if remaining:
                            buffer += remaining.decode("utf-8", errors="replace")
                        break

                    ready, _, _ = select.select([process.stdout], [], [], 1.0)
                    if not ready:
                        continue

                    chunk = os.read(process.stdout.fileno(), 8192)
                    if not chunk:
                        break
                    buffer += chunk.decode("utf-8", errors="replace")

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        if event.get("type") == "stream_event":
                            se = event.get("event", {})
                            se_type = se.get("type", "")

                            if se_type == "content_block_start":
                                cb = se.get("content_block", {})
                                if cb.get("type") == "tool_use":
                                    tool_name = cb.get("name", "")
                                    if tool_name in ("Skill", "Read"):
                                        pending_tool_name = tool_name
                                        accumulated_json = ""
                                    else:
                                        return False

                            elif se_type == "content_block_delta" and pending_tool_name:
                                delta = se.get("delta", {})
                                if delta.get("type") == "input_json_delta":
                                    accumulated_json += delta.get("partial_json", "")
                                    if clean_name in accumulated_json:
                                        return True

                            elif se_type in ("content_block_stop", "message_stop"):
                                if pending_tool_name:
                                    return clean_name in accumulated_json
                                if se_type == "message_stop":
                                    return False

                        elif event.get("type") == "assistant":
                            message = event.get("message", {})
                            for content_item in message.get("content", []):
                                if content_item.get("type") != "tool_use":
                                    continue
                                tool_name = content_item.get("name", "")
                                tool_input = content_item.get("input", {})
                                if (
                                    tool_name == "Skill"
                                    and clean_name in tool_input.get("skill", "")
                                ):
                                    return True
                                elif (
                                    tool_name == "Read"
                                    and clean_name in tool_input.get("file_path", "")
                                ):
                                    return True
                            return False

                        elif event.get("type") == "result":
                            return triggered
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
            return triggered
        finally:
            self.cleanup()

    def cleanup(self):
        if self.temp_command_file and self.temp_command_file.exists():
            try:
                self.temp_command_file.unlink()
            except:
                pass


class KiloEvaluator(BaseEvaluator):
    """Evaluator for Kilo CLI."""

    def __init__(self):
        self.temp_skill_file: Optional[Path] = None

    def run_query(
        self,
        query: str,
        skill_name: str,
        skill_description: str,
        timeout: int,
        project_root: str,
        model: Optional[str] = None,
    ) -> bool:
        unique_id = uuid.uuid4().hex[:8]
        clean_name = f"{skill_name}-{unique_id}"
        # For Kilo, we place skills in .agent/skills/ for discovery
        project_skills_dir = Path(project_root) / ".agent" / "skills"
        self.temp_skill_file = project_skills_dir / f"{clean_name}.md"

        try:
            project_skills_dir.mkdir(parents=True, exist_ok=True)
            skill_content = (
                f"---\n"
                f"name: {skill_name}\n"
                f"description: |\n"
                f"  {skill_description}\n"
                f"---\n\n"
                f"# {skill_name}\n\n"
                f"{skill_description}\n"
            )
            self.temp_skill_file.write_text(skill_content, encoding="utf-8")

            cmd = ["kilo", "run", query, "--print-logs"]
            if model:
                cmd.extend(["-m", model])

            process = subprocess.run(
                cmd, capture_output=True, text=True, cwd=project_root, timeout=timeout
            )

            output = process.stdout + process.stderr
            return clean_name in output or self.temp_skill_file.name in output

        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            print(f"Error running Kilo: {e}", file=sys.stderr)
            return False
        finally:
            self.cleanup()

    def cleanup(self):
        if self.temp_skill_file and self.temp_skill_file.exists():
            try:
                self.temp_skill_file.unlink()
            except:
                pass


class KiroEvaluator(KiloEvaluator):
    """Evaluator for Amazon Kiro IDE agents."""

    def run_query(
        self,
        query: str,
        skill_name: str,
        skill_description: str,
        timeout: int,
        project_root: str,
        model: Optional[str] = None,
    ) -> bool:
        agent_dir = Path(project_root) / ".agent"
        (agent_dir / "skills").mkdir(parents=True, exist_ok=True)
        (agent_dir / "specs").mkdir(parents=True, exist_ok=True)

        # Skill artifact
        skill_file = agent_dir / "skills" / f"{skill_name}.md"
        skill_file.write_text(
            f"# {skill_name}\n\n{skill_description}", encoding="utf-8"
        )

        # Spec artifact (Kiro artifact)
        spec_file = agent_dir / "specs" / f"{skill_name}_spec.md"
        spec_file.write_text(
            f"# Spec for {skill_name}\n\nDescription: {skill_description}",
            encoding="utf-8",
        )

        return super().run_query(
            query, skill_name, skill_description, timeout, project_root, model
        )


class CopilotEvaluator(BaseEvaluator):
    """Evaluator for GitHub Copilot."""

    def run_query(
        self,
        query: str,
        skill_name: str,
        skill_description: str,
        timeout: int,
        project_root: str,
        model: Optional[str] = None,
    ) -> bool:
        skill_file = Path(project_root) / f"{skill_name}_skill.md"
        skill_file.write_text(
            f"# {skill_name}\n\n{skill_description}", encoding="utf-8"
        )

        try:
            cmd = [
                "gh",
                "copilot",
                "explain",
                f"How do I use the {skill_name} skill for: {query}",
            ]
            process = subprocess.run(
                cmd, capture_output=True, text=True, cwd=project_root, timeout=timeout
            )
            output = process.stdout + process.stderr
            return skill_name.lower() in output.lower()
        except:
            return False
        finally:
            if skill_file.exists():
                skill_file.unlink()

    def cleanup(self):
        pass


class SyntheticEvaluator(BaseEvaluator):
    """Evaluator that uses another LLM to predict triggering."""

    def __init__(self, provider: str = "anthropic"):
        self.provider = provider

    def run_query(
        self,
        query: str,
        skill_name: str,
        skill_description: str,
        timeout: int,
        project_root: str,
        model: Optional[str] = None,
    ) -> bool:
        prompt = (
            f"You are a meta-evaluator benchmarking AI agents.\n"
            f"Given the following skill and a user query, determine if an agent "
            f"would use its tools to read or execute this skill.\n\n"
            f"SKILL NAME: {skill_name}\n"
            f"SKILL DESCRIPTION: {skill_description}\n\n"
            f"USER QUERY: {query}\n\n"
            f"Would the agent trigger this skill? Respond ONLY with 'YES' or 'NO'."
        )

        try:
            if self.provider == "google":
                # For Antigravity/Gemini context, we use the internal tool if possible
                # but here we'll assume standard library
                import google.generativeai as genai

                m = genai.GenerativeModel(model or "gemini-1.5-pro")
                resp = m.generate_content(prompt)
                return "YES" in resp.text.upper()
            else:
                import anthropic

                client = anthropic.Anthropic()
                resp = client.messages.create(
                    model=model or "claude-3-5-sonnet-latest",
                    max_tokens=10,
                    messages=[{"role": "user", "content": prompt}],
                )
                return "YES" in resp.content[0].text.upper()
        except Exception as e:
            print(f"Synthetic eval warning: {e}", file=sys.stderr)
            return False

    def cleanup(self):
        pass


class GeminiEvaluator(SyntheticEvaluator):
    """Evaluator for Gemini-based agents like Antigravity."""

    def __init__(self):
        super().__init__(provider="google")


def get_evaluator(agent_name: str) -> BaseEvaluator:
    """Factory to get the correct evaluator."""
    name = agent_name.lower()
    if name == "claude":
        return ClaudeCodeEvaluator()
    elif name == "kilo":
        return KiloEvaluator()
    elif name == "kiro":
        return KiroEvaluator()
    elif name == "copilot":
        return CopilotEvaluator()
    elif name == "gemini":
        return GeminiEvaluator()
    return SyntheticEvaluator()
