---
scope: Snyk Vulnerability Remediation
invariants: [Suggest-only, D7-exempt (app code, not test code)]
related_contracts: [Agent Memory, Security]
---

# Snyk Remediation Skill

## Purpose

Fix vulnerabilities reported by Snyk scanning. This skill covers dependency
upgrades (npm/pip), Snyk Code issues (in-house logic), container image fixes,
and IaC misconfigurations. **D7 does not apply** — this acts on application
code and manifests, not generated test code.

## When to Use

- `agent_memory/snyk-findings.md` has new vulnerability entries
- A user requests Snyk-issue remediation
- CI reports Snyk scan failures

## Workflow

### 1. Read Current Findings

Read `agent_memory/snyk-findings.md` to get the full vulnerability list.

### 2. Classify Each Issue

| Type | Subtype | Remediation Pattern |
|------|---------|---------------------|
| **Open Source** | Dependency vuln | Upgrade to `fixedIn` version; check semver compat |
| **Open Source** | Transitive dep | Add override/resolution in manifest |
| **Snyk Code** | Injection (SQL/XSS) | Parameterize queries, sanitize output |
| **Snyk Code** | Path traversal | Validate/resolve paths, reject `../` |
| **Snyk Code** | Hardcoded secret | Move to env var or secrets manager |
| **Container** | Base image vuln | Switch to `-alpine` or specific patched tag |
| **IaC** | Misconfiguration | Apply recommended fix from Snyk detail |

### 3. Apply Fix (Dependency)

```bash
# npm
npm install <package>@<fixed-version> --save

# pip
pip install <package>==<fixed-version>

# Or update the manifest directly and reinstall
```

### 4. Apply Fix (Code)

For Snyk Code issues, read the surrounding context, then:

- **SQL injection**: Use parameterized queries / ORM
- **XSS**: Use output encoding (`escape`, `DOMPurify`, template auto-escape)
- **Path traversal**: Use `path.resolve()` + reject on `../`
- **Hardcoded secrets**: Replace with `process.env.VAR` / `os.getenv`

### 5. Verify

Run the project's tests after each fix:

```bash
# Detect test command from project
npm test          # Node
pytest            # Python
```

### 6. Log the Fix

Append a row to the Remediation Log in `agent_memory/snyk-findings.md`:

```
| YYYY-MM-DD | SNYK-ID | package-name | upgraded to X.Y.Z | agent-name |
```

## References

- `cherenkov/security/snyk_bridge.py` — report parser
- `agent_memory/snyk-findings.md` — live findings
