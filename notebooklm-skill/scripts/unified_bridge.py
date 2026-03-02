import asyncio
import os
import sys
import json
import argparse
from pathlib import Path
from notebooklm import NotebookLMClient

# Add parent directory to path for config imports
sys.path.append(str(Path(__file__).parent.parent))
try:
    from scripts.config import STATE_FILE, DATA_DIR
except ImportError:
    # Fallback paths if import fails
    DATA_DIR = Path(__file__).parent.parent / "data"
    STATE_FILE = DATA_DIR / "browser_state" / "state.json"


class NotebookLMBridge:
    def __init__(self, storage_path=None):
        self.storage_path = storage_path or str(STATE_FILE)
        self.client = None

    async def __aenter__(self):
        try:
            self.client = await NotebookLMClient.from_storage(self.storage_path)
            await self.client._core.open()
            return self
        except Exception as e:
            print(f"❌ Error initializing NotebookLMClient: {e}")
            sys.exit(1)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client._core.close()

    async def list_notebooks(self):
        notebooks = await self.client.notebooks.list()
        return [
            {
                "id": n.id,
                "title": n.title,
                "url": f"https://notebooklm.google.com/notebook/{n.id}",
            }
            for n in notebooks
        ]

    async def create_notebook(self, title, description=""):
        notebook = await self.client.notebooks.create(title=title)
        return {
            "id": notebook.id,
            "title": notebook.title,
            "url": f"https://notebooklm.google.com/notebook/{notebook.id}",
        }

    async def find_notebook_by_title(self, title):
        notebooks = await self.client.notebooks.list()
        for nb in notebooks:
            if nb.title == title:
                return {
                    "id": nb.id,
                    "url": f"https://notebooklm.google.com/notebook/{nb.id}",
                    "title": nb.title,
                }
        return None

    async def add_source(self, notebook_id, url=None, text=None, title=None):
        if url:
            return await self.client.sources.add_url(notebook_id, url)
        elif text:
            return await self.client.sources.add_text(
                notebook_id, title or "Untitled Source", text
            )
        else:
            raise ValueError("Must provide either url or text")

    async def ask(self, notebook_id, question):
        response = await self.client.chat.ask(notebook_id, question)
        return response.answer

    async def start_research(self, notebook_id, query, mode="fast"):
        """
        mode: 'fast' or 'deep'
        """
        return await self.client.research.start(notebook_id, query, mode=mode)

    async def poll_research(self, notebook_id):
        return await self.client.research.poll(notebook_id)

    async def import_research(self, notebook_id, task_id, sources):
        return await self.client.research.import_sources(notebook_id, task_id, sources)

    async def generate_artifact(self, notebook_id, artifact_type):
        """
        artifact_type: 'audio', 'quiz', 'flashcards', 'mind-map', 'report'
        """
        if artifact_type == "audio":
            status = await self.client.artifacts.generate_audio(notebook_id)
            await self.client.artifacts.wait_for_completion(notebook_id, status.task_id)
            return "Audio generation complete"
        elif artifact_type == "quiz":
            status = await self.client.artifacts.generate_quiz(notebook_id)
            await self.client.artifacts.wait_for_completion(notebook_id, status.task_id)
            return "Quiz generation complete"
        elif artifact_type == "flashcards":
            status = await self.client.artifacts.generate_flashcards(notebook_id)
            await self.client.artifacts.wait_for_completion(notebook_id, status.task_id)
            return "Flashcards generation complete"
        elif artifact_type == "mind-map":
            # Mind map is usually synchronous or returns immediately
            return await self.client.artifacts.generate_mind_map(notebook_id)
        elif artifact_type == "report":
            from notebooklm import ReportFormat

            status = await self.client.artifacts.generate_report(
                notebook_id,
                report_format=ReportFormat.BRIEFING_DOC,
            )
            await self.client.artifacts.wait_for_completion(notebook_id, status.task_id)

            # Download report to temporary file to get content
            temp_path = DATA_DIR / f"temp_report_{status.task_id}.txt"
            try:
                await self.client.artifacts.download_report(
                    notebook_id, str(temp_path), status.task_id
                )
                if temp_path.exists():
                    content = temp_path.read_text(encoding="utf-8")
                    # Optionally delete temp file
                    # temp_path.unlink()
                    return content
            except Exception as e:
                print(f"⚠️ Error downloading report: {e}")

            # Fallback to listing if download fails
            reports = await self.client.artifacts.list_reports(notebook_id)
            if reports:
                latest = reports[-1]
                return (
                    f"Report ID: {latest.id}, Title: {latest.title} (Download failed)"
                )

            return "Report generation complete"
        else:
            raise ValueError(f"Unknown artifact type: {artifact_type}")


async def main():
    parser = argparse.ArgumentParser(description="NotebookLM Bridge CLI")
    parser.add_argument("command", choices=["list", "create", "add", "ask", "artifact"])
    parser.add_argument("--notebook-id", help="Notebook ID")
    parser.add_argument("--title", help="Notebook/Source Title")
    parser.add_argument("--description", help="Notebook Description")
    parser.add_argument("--url", help="Source URL")
    parser.add_argument("--text", help="Source Text")
    parser.add_argument("--question", help="Question to ask")
    parser.add_argument(
        "--type", help="Artifact type (audio, quiz, flashcards, mind-map, report)"
    )
    parser.add_argument("--storage", help="Path to state.json")

    args = parser.parse_args()

    async with NotebookLMBridge(args.storage) as bridge:
        if args.command == "list":
            notebooks = await bridge.list_notebooks()
            print(json.dumps(notebooks, indent=2))
        elif args.command == "create":
            notebook = await bridge.create_notebook(args.title, args.description or "")
            print(json.dumps(notebook, indent=2))
        elif args.command == "add":
            source = await bridge.add_source(
                args.notebook_id, url=args.url, text=args.text, title=args.title
            )
            print("✅ Source added")
        elif args.command == "ask":
            response = await bridge.ask(args.notebook_id, args.question)
            print(response)
        elif args.command == "artifact":
            result = await bridge.generate_artifact(args.notebook_id, args.type)
            if isinstance(result, str):
                print(result)
            else:
                print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
