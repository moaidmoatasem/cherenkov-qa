---
name: k8s-deploy
description: Deploy CHERENKOV to a local k3d cluster and verify conformance passes.
triggers:
  - "k8s deploy"
  - "k3d"
  - "kubernetes"
  - "deploy cherenkov"
  - "make k3d-test"
---

# Skill: k8s-deploy

## Quick path (preferred)
```bash
make k3d-test
```

## Expected outcome
- All pods: `Running`
- Conformance: `PASS` with 0 high-severity findings
- Gate: `PASS`

## Manual steps
See `.qwen/skills/references/k8s-deploy-manual.md` if the Makefile path fails.

## References
- Manual steps + troubleshooting: `.qwen/skills/references/k8s-deploy-manual.md`
- Manifests: `k8s/`
- Go engine: `engine/`
