#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Core Python package + test/lint toolchain (pytest, pytest-cov already pinned here).
# Appium-Python-Client ships no wheel and fails to build here (distutils
# `install_layout` incompatibility with this container's patched setuptools).
# It's only used via subprocess/HTTP in cherenkov/execution/appium_runner.py,
# never imported directly, so unit tests/lint don't need it — skip it.
grep -vi '^Appium-Python-Client' requirements.txt | pip install --user -r /dev/stdin

# Dashboard UI (React/Vite) — needed for `tsc --noEmit` lint and Playwright tests.
if [ -d cherenkov/web/ui ]; then
  (cd cherenkov/web/ui && npm install)
fi
