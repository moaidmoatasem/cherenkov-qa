---
name: certify
description: "Issue a signed CHERENKOV conformance certificate after a clean verify run, proving API spec-vs-server fidelity."
scope: Certification
invariants: [D7]
related_contracts: [Track B/C, Phase 3]
---

# Certify Skill

## Purpose
Run `cherenkov certify` to issue a cryptographically signed conformance certificate after a successful `verify` run. The certificate attests that a specific API version, at a specific commit, passed CHERENKOV's conformance gate.

## When to Use
- You want a tamper-evident artifact proving an API's conformance state at release
- Your compliance programme (SOC 2, ISO 27001, MENA regulations) requires evidence of API contract integrity
- You want to gate a deploy behind a valid certificate
- You want to publish the certificate to a trust registry

## Workflow

### Issue a certificate

```bash
# Certify against current target (uses .cherenkov/report.json from last verify run)
cherenkov certify

# Certify with explicit target URL (runs verify first)
cherenkov certify --target https://api.example.com

# Deep tier with RAG-Triad quality metrics
cherenkov certify --tier deep --rag-report

# Compliance profile (adds MENA / SOC 2 metadata)
cherenkov certify --compliance mena
cherenkov certify --compliance soc2
```

### Certificate tiers

| Tier | Coverage | Use case |
|------|---------|---------|
| `small` (default) | Happy-path + auth scenarios | Fast CI gate |
| `deep` | Full mutation coverage + RAG-Triad | Release sign-off |
| `vision` | Includes visual regression + performance | Full platform audit |

### Certificate format

Issued certificates follow the open `CHERENKOV_CERTIFICATE` spec v1.0 (`docs/specs/CHERENKOV_CERTIFICATE.md`):

```json
{
  "format": "cherenkov/certificate/v1",
  "issued_at": "2026-06-30T12:00:00Z",
  "api_name": "Petstore API",
  "api_version": "3.1.0",
  "commit_sha": "abc123",
  "tier": "deep",
  "verdict": "CONFORMANT",
  "score": 0.97,
  "signature": "...",
  "compliance_profiles": ["soc2", "mena"]
}
```

### Verify a certificate

```bash
cherenkov certify verify --cert .cherenkov/certificate.json
```

Returns: `VALID` / `TAMPERED` / `EXPIRED`.

### CI gate

```yaml
# .github/workflows/certify-gate.yml (fragment)
- name: Issue conformance certificate
  run: cherenkov certify --tier deep --output .cherenkov/certificate.json
- name: Fail if not CONFORMANT
  run: |
    verdict=$(jq -r .verdict .cherenkov/certificate.json)
    [ "$verdict" = "CONFORMANT" ] || exit 1
```

### Badge

After certification, add the badge to your README:

```markdown
![Cherenkov certified](https://img.shields.io/badge/cherenkov-certified-green)
```

## Compliance mapping

The `certify` command maps findings to compliance controls:

```bash
cherenkov certify --compliance soc2 --compliance-report
```

Outputs a compliance mapping table linking each passed gate to its corresponding SOC 2 control (e.g., CC7.2 — Anomalous Activity Detection).

## References
- `cherenkov/cli/commands/certify.py` — CLI command (E3.2)
- `cherenkov/core/certificate.py` — certificate format + signing (E3.1)
- `cherenkov/compliance/` — compliance profile mapping (E3.5)
- `.github/workflows/certify-gate.yml` — CI gate (E3.3)
- `docs/specs/CHERENKOV_CERTIFICATE.md` — open certificate spec v1.0 (E3.4)
- `tests/unit/test_certify.py` — 9 CLI tests + 18 unit tests
