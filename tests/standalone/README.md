# tests/standalone — directly-invoked suites

These suites were moved here from the repository root (2026-06-11 root
cleanup). They are **not** collected by pytest (`norecursedirs` in
`pyproject.toml`) because many depend on services or environment
(Docker, Ollama, ADB, live target API) and are wired into dedicated CI
jobs instead.

Run one directly, from the repo root:

```bash
PYTHONPATH=. python3 -m unittest tests/standalone/test_mcp_policy.py
PYTHONPATH=. python3 tests/standalone/smoke_test_mobile.py
```

The suites referenced by CI jobs (see `.github/workflows/ci.yml`):
`test_copilot_e10`, `test_inference_client`, `smoke_test_mobile`,
`test_mobile_pipeline`, `test_sandbox_providers`, `test_mcp_policy`,
`test_model_runner_client`. The rest run on demand; before relying on
one, check it still passes — several predate the Phase 0–8 refactors.
