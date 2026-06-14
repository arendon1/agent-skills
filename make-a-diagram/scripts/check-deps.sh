#!/usr/bin/env bash
# check-deps.sh — Preflight dependency checker for make-a-diagram
# Usage: bash scripts/check-deps.sh
# Exit 0 if all deps satisfied, 1 if anything missing.

set -euo pipefail

MISSING=()

command -v node >/dev/null 2>&1 || MISSING+=("node (Node.js)")
command -v npx >/dev/null 2>&1 || MISSING+=("npx (bundled with npm)")

# Check mermaid-cli
npx --yes @mermaid-js/mermaid-cli --version >/dev/null 2>&1 || MISSING+=("@mermaid-js/mermaid-cli")

# Check beautiful-mermaid (try import resolution)
node -e "require.resolve('beautiful-mermaid')" >/dev/null 2>&1 || MISSING+=("beautiful-mermaid (npm install beautiful-mermaid)")

echo "=== make-a-diagram dependency check ==="

if [ ${#MISSING[@]} -eq 0 ]; then
    echo "All dependencies satisfied."
    exit 0
fi

echo ""
echo "MISSING DEPENDENCIES:"
for dep in "${MISSING[@]}"; do
    echo "  - $dep"
done
echo ""
echo "Installation hints:"
echo "  Node.js:  https://nodejs.org/en/download"
echo "  mermaid-cli: npx @mermaid-js/mermaid-cli (auto-downloads on first use, or npm install -g @mermaid-js/mermaid-cli)"
echo "  beautiful-mermaid: npm install beautiful-mermaid"
echo ""
exit 1
