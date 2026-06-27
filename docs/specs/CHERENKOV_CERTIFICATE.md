# CHERENKOV Certificate — Open Specification v1.0

> **Status:** STABLE — implementation shipped in `cherenkov/core/certificate.py` v1.0.
> **Why:** the artifact that turns a tool into a standard — portable, signed, verifiable proof
> of what software actually does vs. claims.
> **Date:** 2026-06-27 · Anchor: cherenkov v1.0.0

---

## 1. Purpose

A `VerificationCertificate` is a **self-contained, tamper-evident JSON document** asserting:

> *"At time T, the live API at URL U was probed by CHERENKOV v1.0 and found to have
> verdict V — with the following divergence counts and the following cryptographic
> fingerprint binding this claim to those counts."*

It is honest by construction:
- The fingerprint is **computed from all fields** (excluding itself), so any modification is
  detectable offline without contacting any server.
- The `summary` field records exact per-severity counts; the full evidence is in
  `divergences_json`.
- The `NOT_checked` scope is implicit: anything not in the proof run was not checked.

---

## 2. Wire format (JSON)

All certificates are serialised as a single JSON object with the following top-level fields.

```json
{
  "cert_id":           "<uuid4>",
  "version":           "1.0",
  "issued_at":         "<ISO-8601 UTC>",

  "subject": {
    "base_url":        "<URL of the probed API>",
    "spec_hash":       "<16-hex-char truncated SHA-256 of the OpenAPI spec, or null>"
  },

  "run_id":            "<uuid4 — ties cert to the specific proof run>",

  "summary": {
    "total":    0,
    "high":     0,
    "medium":   0,
    "low":      0,
    "critical": 0
  },

  "verdict":           "PASS | WARN | FAIL",

  "divergences_json":  [ /* array of serialised DivergenceReport objects */ ],

  "fingerprint":       "<64-hex-char SHA-256 of canonical body>",
  "signature":         "<64-hex-char HMAC-SHA256, or empty string if unsigned>"
}
```

### 2.1 Verdict rules

| Verdict | Condition |
|---------|-----------|
| `PASS`  | `summary.high == 0` AND `summary.critical == 0` AND `summary.medium == 0` |
| `WARN`  | `summary.high == 0` AND `summary.critical == 0` AND `summary.medium > 0` |
| `FAIL`  | `summary.high > 0` OR `summary.critical > 0` |

Note: LOW-severity divergences never change the verdict above PASS.

---

## 3. Fingerprint algorithm

The fingerprint provides tamper-evidence offline — no server contact required.

**Steps:**

1. Serialise the certificate as a JSON object with the following fields in
   **lexicographic key order** (i.e. `json.dumps(d, sort_keys=True)`):
   all fields **except** `fingerprint` and `signature`.
2. Encode the serialised string as UTF-8 bytes.
3. Compute SHA-256 of those bytes.
4. Encode as a lowercase hex string (64 characters).

**Python reference:**

```python
import hashlib, json

def compute_fingerprint(cert_dict: dict) -> str:
    body = {k: v for k, v in cert_dict.items()
            if k not in ("fingerprint", "signature")}
    canonical = json.dumps(body, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
```

**Verification** — to check a certificate received from any source:

```python
expected = compute_fingerprint(cert_dict)
assert cert_dict["fingerprint"] == expected, "Certificate tampered"
```

---

## 4. Signature algorithm (optional)

When a `CHERENKOV_CERT_KEY` is provided, the `signature` field carries an
HMAC-SHA256 of the fingerprint.

**Signing:**

```python
import hmac, hashlib

signature = hmac.new(
    key_bytes,           # 32 raw bytes (from hex: bytes.fromhex(key_hex))
    fingerprint.encode(),
    hashlib.sha256,
).hexdigest()
```

**Verification:**

```python
expected_sig = hmac.new(key_bytes, cert["fingerprint"].encode(), hashlib.sha256).hexdigest()
assert hmac.compare_digest(cert["signature"], expected_sig), "Signature invalid"
```

When `signature` is the empty string (`""`), no key was supplied; only fingerprint
integrity is guaranteed.

---

## 5. Issuance flow

```
cherenkov certify [--url <base_url>] [--spec <path>] [--output cert.json]
                  [--signing-key <hex32>] [--fail-on-fail]
```

1. Run the proof loop (`run_proof`) against `base_url`.
2. Compute `summary` from the returned `DivergenceReport` list.
3. Derive `verdict` using the rules in §2.1.
4. Populate all certificate fields.
5. Compute `fingerprint` (§3).
6. If `--signing-key` is present, compute `signature` (§4).
7. Write JSON to `--output` (or stdout).

---

## 6. Offline verification

```
cherenkov certify --verify cert.json [--signing-key <hex32>]
```

Exit codes:
- `0` — fingerprint (and signature, if key supplied) valid.
- `3` — fingerprint mismatch (cert tampered).

---

## 7. Independence guarantee

The open spec in §§2–4 is intentionally self-contained: **any language** can verify a
CHERENKOV Certificate with only SHA-256 and HMAC-SHA256, both universally available.
No cherenkov package is required to verify.

---

## 8. Compliance mapping (E3.5)

See [../compliance/CERT_COMPLIANCE_MAPPING.md](../compliance/CERT_COMPLIANCE_MAPPING.md)
for the authoritative mapping of certificate fields to EU AI Act, ISO/IEC 25010, and
SOC 2 Type II evidence requirements.

Quick reference:

| Cert field / verdict | EU AI Act | SOC 2 CC | ISO/IEC 25010 |
|---|---|---|---|
| `verdict` | Art. 9 §4 (risk-management record) | CC7.2 (anomaly detection) | 4.2.2 (quality characteristics) |
| `fingerprint` | Art. 12 §1 (logging integrity) | CC6.7 (transmission integrity) | — |
| `signature` | Art. 12 §1 | CC6.7 | — |
| `summary.high / critical` | Art. 9 §5 (residual-risk assessment) | CC7.2 | 4.2.8 (reliability) |
| `divergences_json` | Art. 13 §3 (transparency evidence) | CC4.1 (COSO objective) | 4.2.5 (functional correctness) |
| `issued_at` + `run_id` | Art. 12 §2 (audit trail) | CC5.2 (logical access) | — |
