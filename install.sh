#!/usr/bin/env bash
# CHERENKOV one-line install (E1.5)
# Usage:  curl -fsSL https://raw.githubusercontent.com/moaidmoatasem/cherenkov-qa/main/install.sh | bash
set -euo pipefail

REPO="https://github.com/moaidmoatasem/cherenkov-qa"

echo "==> Installing CHERENKOV..."

# Prefer pipx for isolated install; fall back to pip in a venv
if command -v pipx &>/dev/null; then
    pipx install "git+${REPO}.git"
elif command -v pip3 &>/dev/null; then
    pip3 install --user "git+${REPO}.git"
else
    echo "ERROR: neither pipx nor pip3 found. Install Python 3.10+ first." >&2
    exit 1
fi

echo ""
echo "==> Done. Run: cherenkov --help"
