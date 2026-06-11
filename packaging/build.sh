#!/usr/bin/env bash
# Build the CHERENKOV desktop launcher sidecar for macOS/Linux.
# Mirror of build.ps1. Produces packaging/dist/cherenkov-launcher and copies it
# to desktop/src-tauri/binaries/ under the target-triple name Tauri expects for
# externalBin (e.g. cherenkov-launcher-x86_64-unknown-linux-gnu).
set -euo pipefail

cd "$(dirname "$0")"

echo "Building CHERENKOV Desktop Launcher..."

rm -rf build dist

pyinstaller --clean cherenkov.spec

LAUNCHER="dist/cherenkov-launcher"
if [[ ! -f "$LAUNCHER" ]]; then
  # one-dir mode places the binary inside a directory
  LAUNCHER="dist/cherenkov-launcher/cherenkov-launcher"
fi

if [[ ! -f "$LAUNCHER" ]]; then
  echo "ERROR: PyInstaller did not produce dist/cherenkov-launcher" >&2
  exit 1
fi

TRIPLE="$(rustc --print host-tuple 2>/dev/null || rustc -vV | sed -n 's/^host: //p')"
if [[ -z "$TRIPLE" ]]; then
  echo "ERROR: could not determine host target triple (is rustc installed?)" >&2
  exit 1
fi

DEST_DIR="../desktop/src-tauri/binaries"
mkdir -p "$DEST_DIR"
DEST="${DEST_DIR}/cherenkov-launcher-${TRIPLE}"
cp "$LAUNCHER" "$DEST"
chmod +x "$DEST"

echo "Build complete!"
echo "  launcher: packaging/${LAUNCHER#./}"
echo "  sidecar:  desktop/src-tauri/binaries/cherenkov-launcher-${TRIPLE}"
