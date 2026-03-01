#!/usr/bin/env python3
"""Improve a skill description based on eval results.

Takes eval results (from run_eval.py) and generates an improved description
using a vendor-agnostic LLM client.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.llm_client import BaseLLMClient
from scripts.utils import parse_skill_md


def improve_description(
    client: BaseLLMClient,
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list[dict],
    model: str,
    test_results: dict | None = None,
    log_dir: Path | None = None,
    iteration: int | None = None,
) -> str:
    """Call an LLM to improve the description based on eval results."""
    failed_triggers = [
        r for r in eval_results["results"] if r["should_trigger"] and not r["pass"]
    ]
    false_triggers = [
        r
        for r in eval_results["results"]
        if not r["should_trigger"]
        and r["trigger_rate"] > 0.3  # Heuristic for false positive
    ]

    # Build scores summary
    train_score = (
        f"{eval_results['summary']['passed']}/{eval_results['summary']['total']}"
    )
    if test_results:
        test_score = (
            f"{test_results['summary']['passed']}/{test_results['summary']['total']}"
        )
        scores_summary = f"Train: {train_score}, Test: {test_score}"
    else:
        scores_summary = f"Train: {train_score}"

    prompt = f"""You are optimizing a skill description for an AI agent skill called "{skill_name}".
A "skill" is a capability that an agent discovers via its title and description.

Goal: Write a description that triggers for relevant queries and NOT for irrelevant ones.

Current description:
"{current_description}"

Current scores ({scores_summary}):
"""
    if failed_triggers:
        prompt += "\nFAILED TO TRIGGER (should have triggered but didn't):\n"
        for r in failed_triggers:
            prompt += (
                f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
            )

    if false_triggers:
        prompt += "\nFALSE TRIGGERS (triggered but shouldn't have):\n"
        for r in false_triggers:
            prompt += (
                f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
            )

    if history:
        prompt += "\nPREVIOUS ATTEMPTS (do NOT repeat these):\n"
        for h in history:
            prompt += f'- "{h["description"]}"\n'

    prompt += f"""
Skill content for context:
<skill_content>
{skill_content}
</skill_content>

Instructions:
1. Generalize from failures to categories of user intent.
2. Phrase in the imperative ("Use this skill for...").
3. Keep it brief (under 1024 characters).
4. Focus on 'Symptoms' of the problem the user is facing.

Respond ONLY with the new description in <new_description> tags."""

    # Call the LLM abstraction
    response_text = client.create_message(
        model=model, messages=[{"role": "user", "content": prompt}], max_tokens=2048
    )

    # Parse out the <new_description> tags
    match = re.search(
        r"<new_description>(.*?)</new_description>", response_text, re.DOTALL
    )
    description = (
        match.group(1).strip().strip('"') if match else response_text.strip().strip('"')
    )

    # Handle character limit
    if len(description) > 1024:
        shorten_prompt = "That description is too long (>1024 chars). Rewrite it to be shorter while keeping the trigger power. Respond ONLY in <new_description> tags."
        response_text = client.create_message(
            model=model,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response_text},
                {"role": "user", "content": shorten_prompt},
            ],
            max_tokens=1024,
        )
        match = re.search(
            r"<new_description>(.*?)</new_description>", response_text, re.DOTALL
        )
        if match:
            description = match.group(1).strip().strip('"')

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"improve_iter_{iteration or 'unknown'}.json"
        log_file.write_text(
            json.dumps(
                {
                    "iteration": iteration,
                    "description": description,
                    "full_response": response_text,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return description


def main():
    from scripts.llm_client import get_llm_client

    parser = argparse.ArgumentParser(
        description="Improve skill description agent-agnostically"
    )
    parser.add_argument("--eval-results", required=True)
    parser.add_argument("--skill-path", required=True)
    parser.add_argument("--history", default=None)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--provider", default=None, help="Force a provider (google, anthropic)"
    )

    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    eval_results = json.loads(Path(args.eval_results).read_text(encoding="utf-8"))
    history = (
        json.loads(Path(args.history).read_text(encoding="utf-8"))
        if args.history
        else []
    )

    name, _, content = parse_skill_md(skill_path)

    client = get_llm_client(args.provider)
    new_desc = improve_description(
        client=client,
        skill_name=name,
        skill_content=content,
        current_description=eval_results["description"],
        eval_results=eval_results,
        history=history,
        model=args.model,
    )

    print(
        json.dumps(
            {
                "description": new_desc,
                "history": history
                + [
                    {
                        "description": eval_results["description"],
                        "passed": eval_results["summary"]["passed"],
                        "total": eval_results["summary"]["total"],
                    }
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
