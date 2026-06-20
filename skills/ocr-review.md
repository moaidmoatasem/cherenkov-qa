---
scope: OCR Review
invariants: [D7]
related_contracts: [Track A, Phase 1]
---

# OCR Agent Review Skill

## Purpose
Invoke **Alibaba Open Code Review (OCR)** on generated Playwright tests to catch code quality, security, and style issues before HITL review. OCR runs as an optional Gate 7b in the 8-gate pipeline.

## When to Use
- A test survives Gates 1–6 (syntax, structure, AST, assertions, TSC, Prism dry-run)
- You want an LLM agent review of the generated code for quality/safety/style
- You need configurable review rules per project

## Setup

### Install OCR binary
```bash
npm install -g @alibaba-group/open-code-review
# Or download from: https://github.com/alibaba/open-code-review/releases
```

### Enable in CHERENKOV
```bash
export CHERENKOV_OCR_ENABLED=true
# Or set in .env: CHERENKOV_OCR_ENABLED=true
```

### Configure LLM provider
```bash
# Option A: Environment variables (highest priority)
export OCR_LLM_URL=https://api.anthropic.com/v1/messages
export OCR_LLM_TOKEN=sk-ant-xxxxxxxx
export OCR_LLM_MODEL=claude-sonnet-4-6

# Option B: OCR CLI
cherenkov ocr config set model claude-sonnet-4-6
cherenkov ocr config set url https://api.anthropic.com/v1/messages
```

## Usage

### CLI
```bash
# Check OCR installation
cherenkov ocr status

# Test with sample Playwright test
cherenkov ocr test

# Review all generated tests in stub/generated_tests/
cherenkov ocr review

# Review a specific file
cherenkov ocr review --file stub/generated_tests/health.spec.ts

# Review with JSON output (for CI)
cherenkov ocr review --format json
```

### Pipeline Integration
OCR runs as Gate 7b when `CHERENKOV_OCR_ENABLED=true`:
```
Gates: 1.Syntax → 2.Structure → 3.AST → 4.Assertions → 5.TSC → 6.Prism → 7b.OCR → 8.ConsensusOracle
```

### Review Rules (4-Layer Priority)
| Priority | Source | Path |
|----------|--------|------|
| 1 | `--rule` flag | CLI override |
| 2 | Project config | `<repo>/.opencodereview/rule.json` |
| 3 | Global config | `~/.opencodereview/rule.json` |
| 4 | Built-in | embedded rules for Playwright tests |

## OCR Findings Impact
- **Critical**: Gate fails, quality_score reduced by 0.15
- **High**: quality_score reduced by 0.10
- **Medium**: quality_score reduced by 0.05
- **Low/Info**: Annotated only, no score impact

## References
- `cherenkov/review_ocr/` — OCR integration package
- `cherenkov/stages/review.py` — Gate 7b integration at line 320
- `cherenkov/web/routes/ocr_routes.py` — FastAPI OCR endpoints
- `.opencodereview/rule.json` — Project-level OCR rules
- `tests/unit/test_review_ocr.py` — 40 unit tests
