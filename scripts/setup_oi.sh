#!/usr/bin/env bash
# setup_oi.sh — wire CHERENKOV into Open Interpreter's global MCP config
# Usage: bash scripts/setup_oi.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OI_DIR="$HOME/.openinterpreter"
CONFIG_FILE="$OI_DIR/mcp.json"

mkdir -p "$OI_DIR"

# Merge or create the config
if [ -f "$CONFIG_FILE" ]; then
  echo "Existing config found at $CONFIG_FILE — merging cherenkov entry..."
  python3 - <<PYEOF
import json, sys
with open("$CONFIG_FILE") as f:
    config = json.load(f)
config.setdefault("mcpServers", {})["cherenkov"] = {
    "command": "python3",
    "args": ["$REPO_ROOT/cherenkov.py", "mcp", "serve"],
    "cwd": "$REPO_ROOT",
    "env": {"MCP_PROFILE": "full-dev"}
}
with open("$CONFIG_FILE", "w") as f:
    json.dump(config, f, indent=2)
print("Done.")
PYEOF
else
  cat > "$CONFIG_FILE" <<JSON
{
  "mcpServers": {
    "cherenkov": {
      "command": "python3",
      "args": ["$REPO_ROOT/cherenkov.py", "mcp", "serve"],
      "cwd": "$REPO_ROOT",
      "env": {
        "MCP_PROFILE": "full-dev"
      }
    }
  }
}
JSON
  echo "Created $CONFIG_FILE"
fi

echo ""
echo "CHERENKOV is now wired into Open Interpreter."
echo "Restart Open Interpreter and ask: 'list drift findings from cherenkov'"
