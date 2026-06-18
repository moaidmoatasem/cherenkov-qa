#!/usr/bin/env bash
# Quick Start: Qwen Code + CHERENKOV

set -e

echo "Starting CHERENKOV MCP server in the background..."
python3 cherenkov.py mcp serve &
MCP_PID=$!

echo "Waiting for MCP server to initialize..."
for i in $(seq 1 10); do
  python3 -c "import sys, json; sys.stdout.write('{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}\n'); sys.stdout.flush()" | python3 cherenkov.py mcp serve > /dev/null 2>&1 && break
  sleep 1
done

echo "Launching Qwen Code..."
qwen

# Cleanup MCP server on exit
kill $MCP_PID
