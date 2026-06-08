#!/usr/bin/env bash
set -euo pipefail

echo "=== Installing CHERENKOV dev tools ==="

# Install Go
if ! command -v go &>/dev/null; then
    echo "Installing Go 1.22..."
    wget -q https://go.dev/dl/go1.22.5.linux-amd64.tar.gz -O /tmp/go.tar.gz
    sudo rm -rf /usr/local/go
    sudo tar -C /usr/local -xzf /tmp/go.tar.gz
    echo 'export PATH=$PATH:/usr/local/go/bin' | sudo tee /etc/profile.d/go.sh
    export PATH=$PATH:/usr/local/go/bin
    go version
else
    echo "Go already installed: $(go version)"
fi

# Install k3d
if ! command -v k3d &>/dev/null; then
    echo "Installing k3d..."
    wget -q -O - https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
    k3d version
else
    echo "k3d already installed: $(k3d version)"
fi

echo ""
echo "=== Setup complete ==="
echo "Run 'source /etc/profile.d/go.sh' or start a new shell for Go to be on PATH"
