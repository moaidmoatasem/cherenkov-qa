#!/usr/bin/env bash
set -euo pipefail

echo "=== CHERENKOV k3d Setup ==="

# Check prerequisites
command -v k3d >/dev/null 2>&1 || { echo "Error: k3d is not installed. Install from https://k3d.io"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "Error: kubectl is not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Error: docker is not installed."; exit 1; }

echo "Prerequisites OK."

# Clean up any previous cluster
echo "Cleaning up previous cluster..."
k3d cluster delete cherenkov 2>/dev/null || true

# Create cluster
echo "Creating k3d cluster..."
k3d cluster create cherenkov --config k8s/k3d-cluster.yaml

# Build operator image
echo "Building operator image..."
cd operator
docker build -t localhost:5000/cherenkov/operator:latest .
docker push localhost:5000/cherenkov/operator:latest 2>/dev/null || true
cd ..

# Apply manifests
echo "Applying K8s manifests..."
kubectl apply -k k8s/

# Wait for ollama
echo "Waiting for Ollama StatefulSet..."
kubectl wait --for=condition=ready pod -l app=ollama -n cherenkov --timeout=180s || echo "Ollama not ready yet (check GPU availability)"

# Wait for model preloading
echo "Waiting for model preloading Job..."
kubectl wait --for=condition=complete job/ollama-model-pull -n cherenkov --timeout=300s || echo "Model pull incomplete (models may not be loaded)"

echo ""
echo "=== CHERENKOV k3d cluster ready ==="
echo "  kubectl get all -n cherenkov"
echo "  make k3d-test  (run integration tests)"
