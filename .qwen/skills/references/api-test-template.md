# API Test Skeleton Template

```python
"""
Test: <endpoint> <method>
Spec source: <spec_url or spec_file>
Generated: <date>
D7: suggest-only — review before applying
"""
import pytest
import httpx

BASE_URL = "<target_url>"  # Override via env var TARGET_URL

class Test<EndpointName>:
    def test_<scenario>(self, base_url=BASE_URL):
        """<description from spec>"""
        resp = httpx.get(f"{base_url}<path>")
        assert resp.status_code == <spec_derived_status>  # from OpenAPI spec
        # Additional assertions from spec schema
```

## Invariants
- No hardcoded status codes — derive from `get_last_report` or `get_tightening_suggestions`
- No `from cherenkov import` or `import cherenkov` in generated file
- Output as diff block — never auto-apply (D7)

## Eject check
```bash
python3 -c "import ast; ast.parse(open('<test_file>').read()); print('OK')"
grep -r "from cherenkov\|import cherenkov" <test_file> && echo FAIL || echo PASS
```
