"""
Base protocol for usage bridges.

Each bridge module must export:
- SOURCE_HELP: str  — description for --list-sources and interactive prompts
- extract(output_path: str, **kwargs) -> list[dict]
"""

SOURCE_HELP: str


def extract(output_path: str, **kwargs) -> list[dict]:
    raise NotImplementedError("Bridge must implement extract()")
