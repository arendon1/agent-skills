# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich",
#     "typer",
#     "markitdown",
# ]
# ///

import typer
from rich.console import Console
from rich.panel import Panel
from pathlib import Path
from markitdown import MarkItDown
import os
import re

app = typer.Typer()
console = Console()
md_converter = MarkItDown()


def force_download_url(url: str) -> str:
    """Ensure Moodle file links have the forcedownload=1 parameter."""
    if "pluginfile.php" in url and "forcedownload=1" not in url:
        return f"{url}&forcedownload=1" if "?" in url else f"{url}?forcedownload=1"
    return url


def clean_moodle_line(line: str) -> str:
    """Find Moodle URLs in a markdown line and force download if it's a pluginfile."""

    def rewrite(match):
        return force_download_url(match.group(0))

    return re.sub(r"https?://[^\s\)\>]+pluginfile\.php[^\s\)\>]+", rewrite, line)


def extract_moodle_links(sitemap_path: Path):
    """Extract the Moodle links section from an existing sitemap."""
    if not sitemap_path.exists():
        return []

    with open(sitemap_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Look for the section between "## 🌐 Moodle Sections" and the next "##" or end of file
    # Or legacy "> Autoridad: Moodle"
    moodle_section = []
    lines = content.splitlines()
    in_section = False

    for line in lines:
        if line.startswith("## 🌐 Moodle") or line.startswith("> Autoridad: Moodle"):
            in_section = True
            moodle_section.append(line)
            continue
        if in_section:
            if line.startswith("## "):
                break
            # Clean links in the line before adding
            moodle_section.append(clean_moodle_line(line))

    return moodle_section


@app.command()
def sync(course_path: str):
    """
    Sync course content, preserve Moodle links, generate sitemap.md, and convert materials.
    """
    path = Path(course_path)
    if not path.exists():
        console.print(f"[red]Error: Path {course_path} does not exist.[/red]")
        return

    console.print(
        Panel(
            f"🔄 Syncing Course: [bold cyan]{path.name}[/bold cyan]",
            border_style="blue",
        )
    )

    sitemap_path = path / "sitemap.md"
    existing_moodle_links = extract_moodle_links(sitemap_path)

    if not existing_moodle_links:
        # Default placeholder if nothing found
        existing_moodle_links = [
            "## 🌐 Moodle Sections (Permanent Links)",
            "> Autoridad: Moodle",
            "",
        ]

    # Start new sitemap content
    new_sitemap = [f"# Course Sitemap: {path.name}", ""]
    new_sitemap.extend(existing_moodle_links)
    if new_sitemap[-1] != "":
        new_sitemap.append("")

    new_sitemap.append("## 📂 Archivos Locales")
    new_sitemap.append("")

    # Walk through the course structure
    for root, dirs, files in os.walk(path):
        rel_root = Path(root).relative_to(path)

        # Skip hidden/system dirs
        if any(p.startswith(".") for p in rel_root.parts):
            continue

        if rel_root == Path("."):
            continue

        depth = len(rel_root.parts)
        indent = "  " * (depth - 1)
        new_sitemap.append(f"{indent}- **{rel_root.name}/**")

        for file in files:
            if file == "sitemap.md" or file == "AGENTS.md" or file == "README.md":
                continue
            if file.startswith("."):
                continue

            file_path = Path(root) / file
            file_indent = "  " * depth

            # Index file in sitemap
            # Ensure path uses forward slashes for markdown compatibility
            rel_file_path = (rel_root / file).as_posix()
            new_sitemap.append(f"{file_indent}- [{file}]({rel_file_path})")

            # Convert to MD if it's a PDF/DOCX and MD doesn't exist
            if file.lower().endswith((".pdf", ".docx", ".pptx")):
                md_path = file_path.with_suffix(".md")
                if not md_path.exists():
                    try:
                        console.print(f"  [yellow]Converting:[/yellow] {file} -> .md")
                        result = md_converter.convert(str(file_path))
                        if result and result.text_content:
                            with open(md_path, "w", encoding="utf-8") as f:
                                f.write(result.text_content)
                            rel_md_path = (rel_root / md_path.name).as_posix()
                            new_sitemap.append(
                                f"{file_indent}  - [Converted MD]({rel_md_path})"
                            )
                    except Exception as e:
                        console.print(f"  [red]Failed to convert {file}: {e}[/red]")

    # Write sitemap.md
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_sitemap))

    console.print(
        f"\n[bold green]✅ Sync complete![/bold green] Updated `sitemap.md` in {path.name}/"
    )


if __name__ == "__main__":
    app()
