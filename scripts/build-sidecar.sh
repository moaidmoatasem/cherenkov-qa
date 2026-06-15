#!/usr/bin/env bash
set -e

# Change to the root of the repo
cd "$(dirname "$0")/.."

echo "Building CHERENKOV Desktop Sidecar (Bash Wrapper fallback)..."

mkdir -p desktop/src-tauri/binaries
SIDECAR="desktop/src-tauri/binaries/cherenkov-launcher-x86_64-unknown-linux-gnu"

cat << 'EOF' > "$SIDECAR"
#!/usr/bin/env bash
# Tauri sidecar wrapper for CHERENKOV CLI

# Find the Python script relative to where the sidecar might be executed
# Usually the sidecar runs from the Tauri app directory, but just in case, we hardcode the path for local dev testing
# For production, you'd bundle a real Python env.
export PYTHONPATH="/home/moaid/cherenkov-qa:$PYTHONPATH"
exec python3 /home/moaid/cherenkov-qa/cherenkov/cli/core.py "$@"
EOF

chmod +x "$SIDECAR"

echo "Packaging complete. Sidecar generated at $SIDECAR."
echo "Done."
