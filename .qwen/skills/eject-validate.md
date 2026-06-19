---
name: eject-validate
description: Run CHERENKOV's eject workflow to verify tests are portable (no CHERENKOV imports), then validate against the spec. Mirrors skills/eject-standalone.md.
triggers:
  - "eject"
  - "test portability"
  - "standalone test"
  - "strip cherenkov"
---

# Skill: eject-validate

## Purpose
Verify that CHERENKOV-generated tests can run without any CHERENKOV dependencies.  
This is the **anti-lock-in** invariant check.

## Workflow

### Step 1 — Run eject
```bash
python3 cherenkov.py eject --output /tmp/ejected-tests/
```
This strips all CHERENKOV imports and produces standalone test files.

### Step 2 — Validate standalone tests run
```bash
cd /tmp/ejected-tests/
pip install pytest httpx -q
pytest . -v --tb=short 2>&1 | tee /tmp/eject-result.txt
```

### Step 3 — Check for CHERENKOV remnants
```bash
grep -r "from cherenkov" /tmp/ejected-tests/ && echo "FAIL: lock-in detected" || echo "PASS: clean eject"
grep -r "import cherenkov" /tmp/ejected-tests/ && echo "FAIL: lock-in detected" || echo "PASS: clean eject"
```

### Step 4 — Report
Output a summary:
```
Eject Result:
  Files ejected: N
  Tests passing: N/N
  Lock-in violations: 0
  Status: PASS / FAIL
```

**Do NOT modify any test files.** Report-only. (D7 invariant)

## On Failure
If any test imports CHERENKOV, suggest which imports to remove.  
Output as a diff — do NOT auto-apply.

## References
- `skills/eject-standalone.md` — source CHERENKOV skill
- `bin/cherenkov eject` — CLI command
- `.qwen/memory/invariants.md` — anti-lock-in invariant
