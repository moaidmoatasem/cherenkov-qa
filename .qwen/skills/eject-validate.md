---
name: eject-validate
description: Verify CHERENKOV-generated tests are portable — no CHERENKOV imports survive eject.
triggers:
  - "eject"
  - "test portability"
  - "standalone test"
  - "strip cherenkov"
---

# Skill: eject-validate

## Workflow

```bash
# 1 — Eject
python3 cherenkov.py eject --output /tmp/ejected-tests/

# 2 — Validate standalone run
cd /tmp/ejected-tests/
pip install pytest httpx -q
pytest . -v --tb=short 2>&1 | tee /tmp/eject-result.txt

# 3 — Lock-in check
grep -r "from cherenkov\|import cherenkov" /tmp/ejected-tests/ \
  && echo "FAIL: lock-in detected" || echo "PASS: clean eject"
```

Output summary:
```
Eject Result:
  Files ejected: N
  Tests passing: N/N
  Lock-in violations: 0
  Status: PASS / FAIL
```

**Do NOT modify test files.** If violations found, output removal diff only. (D7 invariant)

## References
- `bin/cherenkov eject` — CLI command
- Invariants: `.qwen/memory/invariants.md`
