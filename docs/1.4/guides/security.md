---
title: Security Testing (OWASP)
---

# Security Testing

CHERENKOV includes embedded OWASP mutation payloads for lightweight DAST-style security testing.

## How It Works

When running `cherenkov validate`, CHERENKOV automatically injects OWASP mutation payloads alongside conformance tests:

- SQL injection strings in path/query parameters
- XSS payloads in body fields
- Oversized inputs for buffer testing
- Invalid type coercions
- Authorization boundary tests

## Enable Security Mutations

```bash
cherenkov validate \
  --spec api.yaml \
  --target http://localhost:8000 \
  --security-mutations \   # enable OWASP payloads
  --fail-on-drift
```

## SARIF Output

Security findings appear in the SARIF output and in the GitHub Security tab:

```bash
cherenkov validate --spec api.yaml --target http://localhost:8000 --output ./reports
# Produces reports/test-sarif.json
```

See [SECURITY.md](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/SECURITY.md) for the vulnerability disclosure policy.
