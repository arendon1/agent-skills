import subprocess
import sys
import platform
import os


def run_command(command, shell=True):
    try:
        result = subprocess.run(
            command, shell=shell, capture_output=True, text=True, check=True
        )
        return result.stdout.strip(), True
    except subprocess.CalledProcessError as e:
        return e.stderr.strip() or e.stdout.strip(), False


def check_gh_installed():
    _, success = run_command("gh --version")
    return success


def check_gh_auth():
    output, success = run_command("gh auth status")
    return success, output


def install_gh():
    system = platform.system()
    print(f"Detecting system: {system}")

    if system == "Windows":
        print("Recommended: winget install --id GitHub.cli")
        # Checking if winget is available
        _, winget_exists = run_command("winget --version")
        if winget_exists:
            print("Running: winget install --id GitHub.cli")
            out, success = run_command("winget install --id GitHub.cli")
            return success, out
        else:
            return (
                False,
                "winget not found. Please install manualy from https://github.com/cli/cli/releases",
            )

    elif system == "Darwin":  # MacOS
        print("Recommended: brew install gh")
        _, brew_exists = run_command("brew --version")
        if brew_exists:
            out, success = run_command("brew install gh")
            return success, out
        else:
            return False, "Homebrew not found. Please install manually."

    elif system == "Linux":
        # Check for apt or dnf
        _, apt_exists = run_command("apt --version")
        if apt_exists:
            print(
                'Recommended: sudo mkdir -p -m 755 /etc/apt/keyrings && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && sudo apt update && sudo apt install gh -y'
            )
            return (
                False,
                "Manual installation steps required for Linux (Apt). See output for commands.",
            )

        _, dnf_exists = run_command("dnf --version")
        if dnf_exists:
            print(
                "Recommended: sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo && sudo dnf install gh -y"
            )
            return (
                False,
                "Manual installation steps required for Linux (DNF). See output for commands.",
            )

    return False, f"Unsupported OS for auto-install: {system}"


def main():
    if check_gh_installed():
        print("✅ gh CLI is installed.")
        auth_success, auth_msg = check_gh_auth()
        if auth_success:
            print("✅ gh CLI is authenticated.")
        else:
            print("❌ gh CLI is NOT authenticated.")
            print("Please run: gh auth login")
            sys.exit(1)
    else:
        print("❌ gh CLI is NOT installed.")
        if len(sys.argv) > 1 and sys.argv[1] == "--install":
            success, msg = install_gh()
            if success:
                print("✅ Installation successful. Please restart your terminal.")
            else:
                print(f"❌ Installation failed: {msg}")
        else:
            print("Run with --install to attempt automatic installation.")
            sys.exit(1)


if __name__ == "__main__":
    main()
