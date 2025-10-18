#!/bin/bash
# Auto-install git hooks
# Run this after cloning the repo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "🔧 Installing git hooks..."

# Copy pre-commit hook
if [ -f "$REPO_ROOT/.githooks/pre-commit" ]; then
    cp "$REPO_ROOT/.githooks/pre-commit" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/pre-commit"
    echo "✅ Pre-commit hook installed"
else
    echo "❌ Error: .githooks/pre-commit not found"
    exit 1
fi

echo ""
echo "✅ Git hooks installed successfully!"
echo "   Secrets will be checked before every commit."
