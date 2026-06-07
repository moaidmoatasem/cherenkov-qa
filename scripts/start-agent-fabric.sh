#!/usr/bin/env bash
# Start the full CHERENKOV agent fabric (Phase E — Compose Agents)
# Usage: ./scripts/start-agent-fabric.sh

set -euo pipefail

echo "Starting CHERENKOV agent fabric..."

# Start core services (prism, ollama) + agent services
docker compose --profile agents up -d

echo "Agent fabric is running."
echo "  - explorer-agent: crawling endpoints"
echo "  - healer-agent:  watching for test failures"
echo "  - daemon-agent:  orchestrating healing cycles"

# Attach daemon for live watch
docker compose exec daemon-agent python -m cherenkov daemon --watch
