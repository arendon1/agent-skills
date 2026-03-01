import subprocess
import sys
import json


def run_gh_command(args):
    command = ["gh"] + args
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout, True
    except subprocess.CalledProcessError as e:
        return e.stderr.strip() or e.stdout.strip(), False


def search_code(query, repo=None):
    args = ["search", "code", query]
    if repo:
        args += ["--repo", repo]
    return run_gh_command(args)


def list_issues(repo, state="open"):
    return run_gh_command(
        ["issue", "list", "--repo", repo, "--state", state, "--limit", "10"]
    )


def list_prs(repo, state="open"):
    return run_gh_command(
        ["pr", "list", "--repo", repo, "--state", state, "--limit", "10"]
    )


def get_pr_diff(repo, pr_number):
    return run_gh_command(["pr", "diff", str(pr_number), "--repo", repo])


def main():
    if len(sys.argv) < 2:
        print("Usage: python gh_manager.py <command> <args...>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "search":
        query = sys.argv[2]
        repo = sys.argv[3] if len(sys.argv) > 3 else None
        out, success = search_code(query, repo)
        print(out)
    elif cmd == "issues":
        repo = sys.argv[2]
        out, success = list_issues(repo)
        print(out)
    elif cmd == "prs":
        repo = sys.argv[2]
        out, success = list_prs(repo)
        print(out)
    elif cmd == "pr-diff":
        repo = sys.argv[2]
        pr_num = sys.argv[3]
        out, success = get_pr_diff(repo, pr_num)
        print(out)
    else:
        # Fallback to direct gh call for anything else
        out, success = run_gh_command(sys.argv[1:])
        print(out)


if __name__ == "__main__":
    main()
