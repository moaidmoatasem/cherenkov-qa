param(
    [switch]$SkipBuild
)

Write-Host "=== CHERENKOV k3d Setup ===" -ForegroundColor Cyan

# Check prerequisites
$prereqs = @("k3d", "kubectl", "docker")
foreach ($cmd in $prereqs) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if (-not $found) {
        Write-Error "Error: $cmd is not installed."
        exit 1
    }
}

Write-Host "Prerequisites OK." -ForegroundColor Green

# Clean up previous cluster
Write-Host "Cleaning up previous cluster..."
k3d cluster delete cherenkov 2>$null | Out-Null

# Create cluster
Write-Host "Creating k3d cluster..."
k3d cluster create cherenkov --config k8s/k3d-cluster.yaml
if (-not $?) { exit 1 }

# Build operator image
if (-not $SkipBuild) {
    Write-Host "Building operator image..."
    Push-Location operator
    docker build -t localhost:5000/cherenkov/operator:latest .
    Pop-Location
}

# Apply manifests
Write-Host "Applying K8s manifests..."
kubectl apply -k k8s/
if (-not $?) { exit 1 }

# Wait for ollama
Write-Host "Waiting for Ollama StatefulSet..."
kubectl wait --for=condition=ready pod -l app=ollama -n cherenkov --timeout=180s
if (-not $?) { Write-Warning "Ollama not ready yet (check GPU availability)" }

# Wait for model preloading
Write-Host "Waiting for model preloading Job..."
kubectl wait --for=condition=complete job/ollama-model-pull -n cherenkov --timeout=300s
if (-not $?) { Write-Warning "Model pull incomplete" }

Write-Host ""
Write-Host "=== CHERENKOV k3d cluster ready ===" -ForegroundColor Green
Write-Host "  kubectl get all -n cherenkov"
Write-Host "  make k3d-test"
