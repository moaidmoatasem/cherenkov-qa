#!/usr/bin/env bash
set -e

# Change to the root of the repo
cd "$(dirname "$0")/.."

echo "Building CHERENKOV Desktop Sidecar..."

export TMPDIR=/home/moaid/cherenkov-qa/tmp
export TMP=/home/moaid/cherenkov-qa/tmp
export TEMP=/home/moaid/cherenkov-qa/tmp

# Install PyInstaller
python3 -m pip install --user pyinstaller --break-system-packages

# Build the sidecar as a single file binary
python3 -m PyInstaller --onefile --name cherenkov-launcher cherenkov/cli/core.py

echo "Packaging complete. Moving to Tauri binaries directory..."
mkdir -p desktop/src-tauri/binaries
mv dist/cherenkov-launcher desktop/src-tauri/binaries/cherenkov-launcher-x86_64-unknown-linux-gnu

echo "Done."
