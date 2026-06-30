# k8s-deploy Manual Steps

Use `make k3d-test` first — only fall back to this if the Makefile path fails.

## Prerequisites
- k3d binary at `scripts/k3d`
- kubectl at `~/.local/bin/kubectl` (v1.31.0)
- Docker running
- Go 1.22.5 at `~/.local/opt/go/bin/go`

## Steps

```bash
# 1 — Create cluster
scripts/k3d cluster create cherenkov-test --wait

# 2 — Build and load images
docker build -t cherenkov:dev .
docker build -t cherenkov-mcp:latest -f Dockerfile.mcp .
scripts/k3d image import cherenkov:dev cherenkov-mcp:latest -c cherenkov-test

# 3 — Apply manifests
~/.local/bin/kubectl apply -f k8s/
~/.local/bin/kubectl wait --for=condition=ready pod -l app=cherenkov --timeout=120s

# 4 — Run conformance
python3 cherenkov.py validate --target http://$(kubectl get svc cherenkov -o jsonpath='{.spec.clusterIP}'):8080

# 5 — Cleanup
scripts/k3d cluster delete cherenkov-test
```

## Expected outcome
- All pods: `Running`
- Conformance: `PASS` with 0 high-severity findings

## On failure
```bash
~/.local/bin/kubectl logs -l app=cherenkov --tail=100
```
Report findings — do NOT auto-patch manifests without review.
