import asyncio
import os
import sys
import json
import argparse
from pathlib import Path
from scripts.unified_bridge import NotebookLMBridge


class ResearchOrchestrator:
    def __init__(self, topic, bridge, notebook_id=None, initial_sources=None):
        self.topic = topic
        self.bridge = bridge
        self.notebook_id = notebook_id
        self.initial_sources = initial_sources or []

    async def execute_research(self, mode="deep"):
        print(f"SEARCH Research Topic: {self.topic}")

        # 1. Reuse or Create Notebook (Avoiding Duplicates)
        if not self.notebook_id:
            search_title = f"Research: {self.topic}"
            existing = await self.bridge.find_notebook_by_title(search_title)
            if existing:
                print(f"INFO Reusing existing notebook: {existing['url']}")
                self.notebook_id = existing["id"]
            else:
                print("INFO Creating new research notebook...")
                notebook = await self.bridge.create_notebook(search_title)
                self.notebook_id = notebook["id"]
                print(f"SUCCESS Notebook created: {notebook['url']}")
        else:
            print(f"INFO Using explicitly provided notebook: {self.notebook_id}")

        # 2. Add Baseline Context
        if self.initial_sources:
            print(f"INFO Adding {len(self.initial_sources)} baseline sources...")
            for source in self.initial_sources:
                try:
                    if source.startswith(("http://", "https://")):
                        await self.bridge.add_source(self.notebook_id, url=source)
                    elif os.path.isfile(source):
                        content = Path(source).read_text(encoding="utf-8")
                        await self.bridge.add_source(
                            self.notebook_id,
                            text=content,
                            title=os.path.basename(source),
                        )
                except Exception as e:
                    print(f"  WARNING Error adding source {source}: {e}")

        # 3. Trigger Deep Research
        print(f"ACTION Attempting to trigger {mode.upper()} research via API...")
        task_id = "unknown"
        research_triggered = False
        try:
            research_task = await self.bridge.start_research(
                self.notebook_id, self.topic, mode=mode
            )
            if research_task:
                task_id = research_task.get("task_id", "unknown")
                print(f"  SUCCESS Research session started (ID: {task_id})")
                research_triggered = True
        except Exception as e:
            print(
                f"  WARNING API trigger hit an issue (possibly outdated RPC IDs): {e}"
            )
            print(
                f"  COLLABORATIVE NOTE: If research didn't start automatically, please type '{self.topic}' and click 'Deep Research' in your browser."
            )

        # 4. Collaborative Polling & Automatic Import
        print("ACTION Waiting for research results and collecting knowledge...")
        research_summary = ""
        imported_count = 0
        discovered_len = 0
        poll_count = 0
        max_polls = 10  # Shorter polling for more feedback

        while poll_count < max_polls:
            poll_count += 1
            try:
                status = await self.bridge.poll_research(self.notebook_id)
                if status["status"] == "completed":
                    research_summary = status.get("summary", "")
                    discovered_sources = status.get("sources", [])
                    discovered_len = len(discovered_sources)
                    task_id = status.get("task_id") or task_id

                    print(
                        f"SUCCESS Research completed! Discovered {discovered_len} sources."
                    )

                    if task_id and task_id != "unknown" and discovered_sources:
                        print(f"ACTION Automatically importing discovered knowledge...")
                        imported = await self.bridge.import_research(
                            self.notebook_id, task_id, discovered_sources
                        )
                        imported_count = len(imported)
                        print(f"  SUCCESS {imported_count} sources imported.")
                    break
                elif status["status"] == "in_progress":
                    if poll_count % 2 == 0:  # Check every 2 polls
                        print(
                            f"  ... research is active (Poll {poll_count}/{max_polls})"
                        )
                elif status["status"] == "no_research":
                    if poll_count % 2 == 0:  # Check every 2 polls
                        print(
                            f"  ... waiting for research to be initiated (Poll {poll_count}/{max_polls})"
                        )
                elif status["status"] == "failed":
                    print("ERROR Research task failed on the server.")
                    break
            except Exception as e:
                # If polling fails (outdated RPC), we proceed with synthesis using whatever user has in notebook
                if poll_count >= 2:  # Allow a couple of tries before giving up
                    print(
                        f"  INFO Polling unavailable (API likely updated or transient error: {e}). Proceeding with synthesis of available content."
                    )
                    break
                else:
                    print(f"  WARNING Polling error: {e}. Retrying...")

            await asyncio.sleep(10)

        # 5. Final Synthesis and Briefing
        print("ACTION Synthesizing briefing doc from notebook knowledge...")
        directions = "Synthesis unavailable due to connection issues."
        try:
            directions = await self.bridge.ask(
                self.notebook_id,
                f"Based on the {mode} research findings for '{self.topic}', provide a technical briefing on OpenCode CLI parallel agents and multi-agent workflows.",
            )
        except Exception as e:
            print(f"  WARNING Synthesis error: {e}")

        # 6. Final Report Artifact
        print("ACTION Generating final report artifact...")
        report_content = "Report generation failed."
        try:
            report_content = await self.bridge.generate_artifact(
                self.notebook_id, "report"
            )
        except Exception as e:
            print(f"  WARNING Report generation error: {e}")

        return {
            "notebook_id": self.notebook_id,
            "notebook_url": f"https://notebooklm.google.com/notebook/{self.notebook_id}",
            "topic": self.topic,
            "summary": research_summary[:500]
            if research_summary
            else "Automated polling failed, but synthesis attempted.",
            "synthesis": directions,
            "sources_discovered": discovered_len,
            "sources_imported": imported_count,
        }


async def main():
    parser = argparse.ArgumentParser(description="NotebookLM Research Orchestrator")
    parser.add_argument("topic", help="Topic to research")
    parser.add_argument("--notebook-id", help="Existing notebook ID to use")
    parser.add_argument(
        "--sources", help="Initial sources (comma separated, URL or path)"
    )
    parser.add_argument("--storage", help="Path to state.json")
    parser.add_argument("--mode", default="deep", help="Research mode: fast or deep")

    args = parser.parse_args()

    sources = args.sources.split(",") if args.sources else []

    async with NotebookLMBridge(args.storage) as bridge:
        orchestrator = ResearchOrchestrator(
            args.topic, bridge, args.notebook_id, sources
        )
        result = await orchestrator.execute_research(mode=args.mode)
        # Output final result as JSON for workflow consumption
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
