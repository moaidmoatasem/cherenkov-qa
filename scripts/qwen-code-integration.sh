#!/usr/bin/env bash
# Quick Start: Qwen Code + CHERENKOV

set -e

echo "Starting CHERENKOV MCP server in the background..."
python3 cherenkov.py mcp serve &
MCP_PID=$!

echo "Waiting for MCP server to initialize..."
sleep 2

echo "Launching Qwen Code..."
qwen serve

# Cleanup MCP server on exit
kill $MCP_PID
