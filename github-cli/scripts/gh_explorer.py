import subprocess
import json
import os
import sys
import re
import tempfile
import argparse
from pathlib import Path

# Complexity Thresholds
MAX_DISK_USAGE_KB = 1048576  # 1GB
MAX_FILE_COUNT = 500


def run_gh_command(args, return_error=False):
    command = ["gh"] + args
    try:
        # Explicitly set encoding to utf-8 to avoid Windows CP1252 issues
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, encoding="utf-8"
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        if return_error:
            return f"ERROR: {e.stderr.strip() or e.stdout.strip()}"
        print(f"Error running gh {' '.join(args)}: {e.stderr}", file=sys.stderr)
        return None


def parse_repo_url(url):
    pattern = r"(?:https?://github\.com/)?([^/]+)/([^/\s?#]+)"
    match = re.search(pattern, url)
    if match:
        return f"{match.group(1)}/{match.group(2).replace('.git', '')}"
    return url


def get_repo_metadata(repo):
    output = run_gh_command(
        [
            "repo",
            "view",
            repo,
            "--json",
            "name,description,url,primaryLanguage,diskUsage",
        ]
    )
    if output:
        return json.loads(output)
    return None


import base64


def get_readme(repo):
    # Use API to get raw content
    output = run_gh_command(["api", f"repos/{repo}/readme", "--jq", ".content"])
    if output and not output.startswith("ERROR:"):
        try:
            # gh api returns base64 with newlines sometimes
            encoded = output.replace("\n", "").strip()
            return base64.b64decode(encoded).decode("utf-8")
        except Exception as e:
            print(f"⚠️ README decode failed: {e}")
    # Fallback to rendered view if API fails
    return run_gh_command(["repo", "view", repo])


def get_repo_tree(repo):
    repo_info = run_gh_command(["repo", "view", repo, "--json", "defaultBranchRef"])
    if not repo_info:
        return None
    branch_data = json.loads(repo_info)
    if not branch_data.get("defaultBranchRef"):
        return None
    branch = branch_data["defaultBranchRef"]["name"]

    output = run_gh_command(["api", f"repos/{repo}/git/trees/{branch}?recursive=1"])
    if output:
        return json.loads(output)
    return None


def is_low_complexity(metadata, tree_data):
    disk_usage = metadata.get("diskUsage", 0)
    file_count = len(
        [item for item in tree_data.get("tree", []) if item["type"] == "blob"]
    )
    print(f"📊 Complexity Audit: {disk_usage}KB, {file_count} files")
    return disk_usage <= MAX_DISK_USAGE_KB and file_count <= MAX_FILE_COUNT


def deep_analyze_local(path, mode="usage"):
    results = {
        "configurations": {},
        "cli_commands": [],
        "api_signatures": [],
        "examples": [],
        "dev_insights": {},
    }
    p = Path(path)

    # 1. Configuration Deep Dive
    pkg_json = p / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                results["configurations"]["package.json"] = {
                    "scripts": data.get("scripts", {}),
                    "dependencies": data.get("dependencies", {}),
                    "devDependencies": data.get("devDependencies", {}),
                    "bin": data.get("bin", {}),
                }
        except:
            pass

    # 2. Heuristic Code Analysis
    for ext in [".ts", ".js", ".py", ".go"]:
        for f in p.rglob(f"*{ext}"):
            if any(
                x in str(f) for x in ["node_modules", "dist", "venv", "__pycache__"]
            ):
                continue
            try:
                content = f.read_text(encoding="utf-8")

                if mode == "usage":
                    # Look for CLI command registration
                    cmds = re.findall(r"\.command\(['\"]([^'\"]+)['\"]", content)
                    results["cli_commands"].extend(cmds)
                    # Look for exports (API surface)
                    exports = re.findall(
                        r"export (?:async )?(?:function|class|const) ([a-zA-Z0-9_]+)",
                        content,
                    )
                    results["api_signatures"].extend(exports[:5])
                else:
                    # Dev mode: look for test patterns, internal structure
                    if "describe(" in content or "test(" in content or "it(" in content:
                        results["dev_insights"]["has_tests"] = True
                    if "import" in content or "require" in content:
                        results["dev_insights"]["imports"] = (
                            results["dev_insights"].get("imports", 0) + 1
                        )

                if (len(results["cli_commands"]) + len(results["api_signatures"])) > 50:
                    break
            except:
                pass

    # 3. Look for Examples/Tests
    target_dirs = (
        ["examples", "samples"] if mode == "usage" else ["tests", "specs", "docs"]
    )
    for ed in target_dirs:
        ed_path = p / ed
        if ed_path.exists() and ed_path.is_dir():
            for f in ed_path.rglob("*.*"):
                if f.suffix in [".ts", ".js", ".py", ".md"]:
                    try:
                        results["examples"].append(
                            {
                                "file": str(f.relative_to(path)),
                                "content": f.read_text(encoding="utf-8")[:1000],
                            }
                        )
                    except:
                        pass
                if len(results["examples"]) > 5:
                    break

    return results


def generate_knowledge_artifact(
    repo_metadata, tree_data, mode="usage", deep_results=None
):
    artifact = f"# Technical Knowledge ({mode.upper()}): {repo_metadata['name']}\n\n"
    artifact += f"> [!NOTE]\n"
    artifact += f"> This artifact was generated via `github-cli` deep analysis (Mode: {mode}).\n"
    artifact += f"> It provides actionable expertise for an agent to {'use' if mode == 'usage' else 'develop/contribute to'} the tool.\n\n"

    artifact += f"## 📋 Overview\n"
    artifact += f"- **URL**: {repo_metadata['url']}\n"
    artifact += f"- **Description**: {repo_metadata['description']}\n"
    artifact += f"- **Primary Language**: {repo_metadata['primaryLanguage'].get('name', 'N/A') if repo_metadata.get('primaryLanguage') else 'N/A'}\n"
    artifact += f"- **Complexity**: {repo_metadata.get('diskUsage', 0)}KB, {len(tree_data.get('tree', []))} nodes\n\n"

    if deep_results:
        artifact += f"## 🔧 {mode.capitalize()} Expertise\n\n"

        if mode == "usage":
            # Usage specific info
            bins = deep_results["configurations"].get("package.json", {}).get("bin", {})
            if bins or deep_results["cli_commands"]:
                artifact += "### 🕹️ CLI Interface\n"
                if isinstance(bins, dict):
                    for b in bins:
                        artifact += f"- Binary: `{b}`\n"
                elif bins:
                    artifact += f"- Binary: `{bins}`\n"
                for cmd in list(set(deep_results["cli_commands"])):
                    artifact += f"- Command Pattern: `{cmd}`\n"
                artifact += "\n"

            if deep_results["api_signatures"]:
                artifact += "### 🧩 Public API Surface\n"
                for sig in list(set(deep_results["api_signatures"]))[:20]:
                    artifact += f"- `{sig}`\n"
                artifact += "\n"
        else:
            # Dev specific info
            scripts = (
                deep_results["configurations"]
                .get("package.json", {})
                .get("scripts", {})
            )
            if scripts:
                artifact += "### 📜 Development Scripts\n"
                dev_scripts = {
                    k: v
                    for k, v in scripts.items()
                    if any(x in k for x in ["test", "lint", "build", "dev", "watch"])
                }
                for s, c in dev_scripts.items():
                    artifact += f"- `npm run {s}`: `{c}`\n"
                artifact += "\n"

            deps = (
                deep_results["configurations"]
                .get("package.json", {})
                .get("devDependencies", {})
            )
            if deps:
                artifact += "### 📦 Dev Dependencies\n"
                artifact += (
                    ", ".join([f"`{d}`" for d in list(deps.keys())[:15]]) + "\n\n"
                )

        # Shared Examples section but filtered by mode target dirs
        if deep_results["examples"]:
            artifact += f"### 💡 {mode.capitalize()} Patterns & Examples\n"
            for ex in deep_results["examples"]:
                artifact += f"#### `{ex['file']}`\n"
                artifact += f"```\n{ex['content']}\n```\n\n"

    artifact += "## 📂 Repository Landmarks\n"
    interesting_patterns = [
        r"package\.json",
        r"pyproject\.toml",
        r"src/index",
        r"src/main",
        r"SKILL\.md",
        r"README",
    ]
    if mode == "dev":
        interesting_patterns += [r"test", r"spec", r"\.env", r"contribut", r"docker"]

    for item in tree_data.get("tree", []):
        if item["type"] == "blob":
            if any(re.search(p, item["path"], re.I) for p in interesting_patterns):
                artifact += f"- `{item['path']}`\n"

    artifact += "\n## 📖 Specialized Documentation\n"
    readme = repo_metadata.get("readme", "").replace("\r\n", "\n")
    # Split by headers but keep them.
    # Logic: [text_before, header1, content1, header2, content2, ...]
    parts = re.split(r"(^\s*#+\s+.*)", readme, flags=re.MULTILINE)

    if mode == "usage":
        target_sections = ["usage", "install", "quick start", "api", "cli", "example"]
    else:
        target_sections = [
            "contribut",
            "build",
            "test",
            "develop",
            "setup",
            "architect",
            "internal",
            "changelog",
        ]

    # We iterate over headers (indices 1, 3, 5...)
    found_count = 0
    for i in range(1, len(parts), 2):
        header = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""
        # print(f"📄 Found header: {header.strip()}")
        if any(t in header.lower() for t in target_sections):
            artifact += f"\n{header}\n{content}\n"
            found_count += 1

    # print(f"📄 Found {len(parts) // 2} sections, matched {found_count} for mode {mode}")

    return artifact


def main():
    parser = argparse.ArgumentParser(
        description="Advanced GitHub Repository Expertise Extractor"
    )
    parser.add_argument("repo_url", help="GitHub repository URL or owner/repo")
    parser.add_argument(
        "--mode",
        choices=["usage", "dev"],
        default="usage",
        help="Goal: learn how to use vs how to develop",
    )
    args = parser.parse_args()

    repo = parse_repo_url(args.repo_url)
    print(f"🔍 Analyzing {repo} [Intent: {args.mode}]...")

    metadata = get_repo_metadata(repo)
    if not metadata:
        print(f"❌ Failed to fetch metadata for {repo}")
        sys.exit(1)

    metadata["readme"] = get_readme(repo) or ""
    tree = get_repo_tree(repo)

    deep_results = None
    if tree and is_low_complexity(metadata, tree):
        print(
            f"🚀 Low-complexity repo. Initiating ephemeral clone for {args.mode} analysis."
        )
        with tempfile.TemporaryDirectory() as tmp_parent:
            tmp_dir = os.path.join(tmp_parent, "repo")
            clone_output = run_gh_command(
                ["repo", "clone", repo, tmp_dir], return_error=True
            )
            if isinstance(clone_output, str) and clone_output.startswith("ERROR:"):
                print(f"⚠️ Clone failed: {clone_output}. Falling back to API mapping.")
            else:
                if os.path.exists(tmp_dir):
                    deep_results = deep_analyze_local(tmp_dir, mode=args.mode)
                    print("✅ Deep analysis complete.")
                else:
                    print("⚠️ Clone dir missing.")
    else:
        print("📂 High complexity repo. Using API metadata mapping only.")

    knowledge_doc = generate_knowledge_artifact(
        metadata, tree, mode=args.mode, deep_results=deep_results
    )

    out_file = f"knowledge_{metadata['name'].replace('-', '_')}_{args.mode}.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(knowledge_doc)

    print(f"✅ Expertise artifact generated ({args.mode}): {out_file}")


if __name__ == "__main__":
    main()
