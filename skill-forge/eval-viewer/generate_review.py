#!/usr/bin/env python3
"""
Generate an interactive HTML review page for skill evaluation results.

Usage:
    python generate_review.py <workspace> --skill-name <name> [--benchmark <benchmark.json>]
    python generate_review.py <workspace> --skill-name <name> --static <output.html>

For Cowork/headless environments, use --static to write a standalone HTML file.
"""

import argparse
import json
import sys
from pathlib import Path


def generate_html(workspace: Path, skill_name: str, benchmark_path: Path | None = None, static_output: Path | None = None):
    """Generate the interactive review HTML."""

    # Load benchmark data if provided
    benchmark = {}
    if benchmark_path and benchmark_path.exists():
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))

    # Discover eval directories
    eval_dirs = sorted(workspace.glob("eval-*"))
    if not eval_dirs:
        eval_dirs = sorted((workspace / "runs").glob("eval-*")) if (workspace / "runs").exists() else []

    # Build the HTML
    html_parts = []

    # Header
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skill Eval Review: """ + skill_name + """</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #00d4ff; border-bottom: 2px solid #00d4ff; padding-bottom: 10px; }
        h2 { color: #e94560; margin-top: 30px; }
        .tabs { display: flex; gap: 10px; margin: 20px 0; }
        .tab { padding: 12px 24px; background: #16213e; border: none; color: #eee; cursor: pointer; border-radius: 8px 8px 0 0; font-size: 16px; }
        .tab.active { background: #0f3460; color: #00d4ff; }
        .tab-content { display: none; background: #0f3460; padding: 20px; border-radius: 0 8px 8px 8px; }
        .tab-content.active { display: block; }
        .eval-nav { display: flex; justify-content: space-between; align-items: center; margin: 20px 0; padding: 15px; background: #16213e; border-radius: 8px; }
        .eval-nav button { padding: 10px 20px; background: #e94560; border: none; color: white; cursor: pointer; border-radius: 6px; }
        .eval-nav button:disabled { opacity: 0.5; cursor: not-allowed; }
        .eval-title { font-size: 24px; color: #00d4ff; }
        .prompt { background: #16213e; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #e94560; }
        .prompt-label { color: #e94560; font-weight: bold; margin-bottom: 5px; }
        .output-section { background: #16213e; padding: 15px; border-radius: 8px; margin: 10px 0; }
        .config-label { font-size: 18px; padding: 8px 16px; border-radius: 6px; display: inline-block; margin: 5px 0; }
        .with-skill { background: #00d4ff; color: #1a1a2e; }
        .without-skill { background: #e94560; color: white; }
        .files-list { list-style: none; padding: 0; }
        .files-list li { padding: 8px; background: #1a1a2e; margin: 5px 0; border-radius: 4px; }
        .file-preview { background: #1a1a2e; padding: 15px; border-radius: 8px; margin: 10px 0; max-height: 400px; overflow-y: auto; white-space: pre-wrap; font-family: monospace; font-size: 13px; }
        .grading { background: #1a1a2e; padding: 15px; border-radius: 8px; margin: 10px 0; }
        .assertion { padding: 10px; margin: 5px 0; border-radius: 4px; }
        .assertion.pass { background: rgba(0, 255, 100, 0.2); border-left: 4px solid #00ff64; }
        .assertion.fail { background: rgba(255, 100, 100, 0.2); border-left: 4px solid #ff6464; }
        .assertion-text { font-weight: bold; }
        .assertion-evidence { font-size: 13px; color: #aaa; margin-top: 5px; }
        .feedback-section { margin-top: 20px; }
        .feedback-section textarea { width: 100%; height: 120px; background: #16213e; color: #eee; border: 1px solid #333; border-radius: 8px; padding: 15px; font-size: 14px; resize: vertical; }
        .benchmark-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .benchmark-table th, .benchmark-table td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        .benchmark-table th { background: #16213e; color: #00d4ff; }
        .benchmark-table tr:hover { background: rgba(0, 212, 255, 0.1); }
        .delta { color: #00ff64; font-weight: bold; }
        .notes { background: #16213e; padding: 15px; border-radius: 8px; margin: 10px 0; }
        .note-item { padding: 8px; margin: 5px 0; border-left: 3px solid #e94560; }
        .submit-btn { background: #00d4ff; color: #1a1a2e; padding: 15px 30px; border: none; border-radius: 8px; font-size: 18px; cursor: pointer; margin: 20px 0; }
        .submit-btn:hover { background: #00b8e6; }
        .previous-output { border-top: 2px dashed #666; margin-top: 20px; padding-top: 20px; }
        .previous-label { color: #888; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Skill Eval Review: """ + skill_name + """</h1>
        <div class="tabs">
            <button class="tab active" onclick="showTab('outputs')">Outputs</button>
            <button class="tab" onclick="showTab('benchmark')">Benchmark</button>
        </div>
""")

    # Outputs tab
    html_parts.append('        <div id="outputs" class="tab-content active">')
    html_parts.append('            <div class="eval-nav">')
    html_parts.append('                <button onclick="prevEval()">&#8592; Previous</button>')
    html_parts.append('                <span class="eval-title" id="evalTitle">Eval 0</span>')
    html_parts.append('                <button onclick="nextEval()">Next &#8594;</button>')
    html_parts.append('            </div>')

    for idx, eval_dir in enumerate(eval_dirs):
        eval_id = eval_dir.name
        metadata_path = eval_dir / "eval_metadata.json"
        metadata = {}
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except:
                pass

        html_parts.append(f'            <div class="eval-container" id="eval-{idx}" style="display: {"block" if idx == 0 else "none"};">')

        # Prompt
        prompt_text = metadata.get("prompt", "No prompt recorded")
        html_parts.append(f'''
                <div class="prompt">
                    <div class="prompt-label">PROMPT:</div>
                    {prompt_text}
                </div>
''')

        # Find configurations
        config_dirs = sorted([d for d in eval_dir.iterdir() if d.is_dir() and list(d.glob("run-*"))])

        for config_dir in config_dirs:
            config_name = config_dir.name
            run_dirs = sorted(config_dir.glob("run-*"))
            label_class = "with-skill" if "with_skill" in config_name else "without_skill"
            label_text = "With Skill" if "with_skill" in config_name else "Without Skill"

            html_parts.append(f'''
                <div class="output-section">
                    <span class="config-label {label_class}">{label_text}</span>
''')

            for run_dir in run_dirs:
                # Find output files
                outputs_dir = run_dir / "outputs"
                grading_path = run_dir / "grading.json"

                if outputs_dir.exists():
                    files = list(outputs_dir.iterdir())
                    if files:
                        html_parts.append(f'''
                    <div style="margin: 15px 0;">
                        <strong>Run {run_dir.name}:</strong>
                        <ul class="files-list">
''')
                        for f in files:
                            html_parts.append(f'<li>{f.name}</li>')
                        html_parts.append('                        </ul>')

                        # Try to preview text files
                        for f in files:
                            if f.suffix in ['.txt', '.md', '.json', '.csv', '.py', '.js']:
                                try:
                                    content = f.read_text(encoding="utf-8", errors="replace")[:2000]
                                    html_parts.append(f'''
                        <div class="file-preview"><strong>{f.name}:</strong>\n{content}</div>
''')
                                except:
                                    pass

                        html_parts.append('                    </div>')

                # Grading if exists
                if grading_path.exists():
                    try:
                        grading = json.loads(grading_path.read_text(encoding="utf-8"))
                        expectations = grading.get("expectations", [])
                        summary = grading.get("summary", {})

                        html_parts.append(f'''
                    <div class="grading">
                        <strong>Grading ({summary.get("passed", 0)}/{summary.get("total", 0)} passed, {summary.get("pass_rate", 0)*100:.0f}%)</strong>
''')
                        for exp in expectations:
                            status = "pass" if exp.get("passed") else "fail"
                            html_parts.append(f'''
                        <div class="assertion {status}">
                            <div class="assertion-text">{"✅" if exp.get("passed") else "❌"} {exp.get("text", "")}</div>
                            <div class="assertion-evidence">{exp.get("evidence", "")}</div>
                        </div>
''')
                        html_parts.append('                    </div>')
                    except:
                        pass

            html_parts.append('                </div>')

        # Feedback
        html_parts.append(f'''
                <div class="feedback-section">
                    <label for="feedback-{idx}">Your Feedback:</label>
                    <textarea id="feedback-{idx}" placeholder="Leave your feedback here..."></textarea>
                </div>
''')
        html_parts.append('            </div>')

    html_parts.append('        </div>')

    # Benchmark tab
    html_parts.append('        <div id="benchmark" class="tab-content">')

    if benchmark:
        run_summary = benchmark.get("run_summary", {})
        html_parts.append('''
            <table class="benchmark-table">
                <tr>
                    <th>Configuration</th>
                    <th>Pass Rate</th>
                    <th>Time (s)</th>
                    <th>Tokens</th>
                </tr>
''')
        configs = [k for k in run_summary if k != "delta"]
        for config in configs:
            stats = run_summary[config]
            pr = stats.get("pass_rate", {})
            time = stats.get("time_seconds", {})
            tokens = stats.get("tokens", {})
            html_parts.append(f'''
                <tr>
                    <td>{config.replace("_", " ").title()}</td>
                    <td>{pr.get("mean", 0)*100:.1f}% ± {pr.get("stddev", 0)*100:.1f}%</td>
                    <td>{time.get("mean", 0):.1f} ± {time.get("stddev", 0):.1f}</td>
                    <td>{tokens.get("mean", 0):.0f} ± {tokens.get("stddev", 0):.0f}</td>
                </tr>
''')

        delta = run_summary.get("delta", {})
        if delta:
            html_parts.append(f'''
                <tr style="background: rgba(0, 255, 100, 0.1);">
                    <td><strong>Delta</strong></td>
                    <td class="delta">{delta.get("pass_rate", "—")}</td>
                    <td class="delta">{delta.get("time_seconds", "—")}</td>
                    <td class="delta">{delta.get("tokens", "—")}</td>
                </tr>
''')

        html_parts.append('            </table>')

        notes = benchmark.get("notes", [])
        if notes:
            html_parts.append('''
            <h3>Analysis Notes</h3>
            <div class="notes">
''')
            for note in notes:
                html_parts.append(f'<div class="note-item">{note}</div>')
            html_parts.append('            </div>')
    else:
        html_parts.append('<p>No benchmark data available. Run evaluations first.</p>')

    html_parts.append('        </div>')

    # JavaScript
    html_parts.append("""
        <button class="submit-btn" onclick="submitFeedback()">Submit All Reviews</button>
    </div>

    <script>
        let currentEval = 0;
        const totalEvals = document.querySelectorAll('.eval-container').length;

        function showTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }

        function showEval(idx) {
            document.querySelectorAll('.eval-container').forEach(ec => ec.style.display = 'none');
            document.getElementById('eval-' + idx).style.display = 'block';
            document.getElementById('evalTitle').textContent = 'Eval ' + (idx + 1) + ' of ' + totalEvals;
            currentEval = idx;
        }

        function prevEval() {
            if (currentEval > 0) showEval(currentEval - 1);
        }

        function nextEval() {
            if (currentEval < totalEvals - 1) showEval(currentEval + 1);
        }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowLeft') prevEval();
            if (e.key === 'ArrowRight') nextEval();
        });

        function submitFeedback() {
            const feedback = [];
            for (let i = 0; i < totalEvals; i++) {
                const textarea = document.getElementById('feedback-' + i);
                if (textarea && textarea.value.trim()) {
                    feedback.push({
                        eval_index: i,
                        feedback: textarea.value.trim(),
                        timestamp: new Date().toISOString()
                    });
                }
            }
            const blob = new Blob([JSON.stringify({reviews: feedback, status: 'complete'}, null, 2)],
                {type: 'application/json'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'feedback.json';
            a.click();
            alert('Feedback submitted! Downloaded feedback.json');
        }
    </script>
</body>
</html>
""")

    return "\n".join(html_parts)


def main():
    parser = argparse.ArgumentParser(description="Generate interactive HTML review page for skill evaluations")
    parser.add_argument("workspace", type=Path, help="Path to the workspace containing eval-* directories")
    parser.add_argument("--skill-name", required=True, help="Name of the skill being evaluated")
    parser.add_argument("--benchmark", type=Path, help="Path to benchmark.json")
    parser.add_argument("--static", type=Path, help="Write standalone HTML to this path (for headless environments)")
    parser.add_argument("--previous-workspace", type=Path, help="Path to previous iteration's workspace for comparison")

    args = parser.parse_args()

    if not args.workspace.exists():
        print(f"Error: Workspace not found: {args.workspace}", file=sys.stderr)
        sys.exit(1)

    html = generate_html(args.workspace, args.skill_name, args.benchmark, args.static)

    if args.static:
        args.static.write_text(html, encoding="utf-8")
        print(f"Static HTML written to: {args.static}")
    else:
        try:
            import webbrowser
            import tempfile
            import os

            # Write to temp file and open
            temp_path = Path(tempfile.gettempdir()) / f"skill_eval_review_{args.skill_name}.html"
            temp_path.write_text(html, encoding="utf-8")
            webbrowser.open(str(temp_path))
            print(f"Opened review in browser: {temp_path}")
        except Exception as e:
            # Fallback: write to current directory
            output_path = Path.cwd() / f"skill_eval_review_{args.skill_name}.html"
            output_path.write_text(html, encoding="utf-8")
            print(f"Browser not available. Written to: {output_path}")


if __name__ == "__main__":
    main()