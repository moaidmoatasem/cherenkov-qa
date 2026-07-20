# CHERENKOV Certificate — Compliance Mapping (E3.5)

> Maps `VerificationCertificate` fields to specific articles/controls in
> **EU AI Act (2024/1689)**, **SOC 2 Type II (Trust Services Criteria 2022)**,
> **ISO/IEC 25010:2023 (SQuaRE)**, **ISO/IEC 42001:2023**, the **OWASP AI Testing
> Guide v1**, and the **OWASP Top 10 for LLM Applications**.
>
> Each row cites the exact provision, states what the certificate field provides,
> and notes any gap or caveat.

---

## EU AI Act (Regulation 2024/1689)

| Provision | Title | Cert field(s) | What the cert provides | Gap / caveat |
|---|---|---|---|---|
| Art. 9 §4 | Risk-management system — record of residual risk | `verdict`, `summary` | Machine-readable record of whether residual divergences exist and at which severity | Does not cover risk acceptability threshold — integrator must set `--fail-on-fail` as acceptance policy |
| Art. 9 §5 | Residual-risk evaluation | `summary.high`, `summary.critical`, `divergences_json` | Enumerated list of found divergences with per-item evidence and repro steps | Coverage is bounded by the proof-run scope; does not replace full V&V |
| Art. 12 §1 | Logging — authenticity & integrity | `fingerprint`, `signature` | SHA-256 fingerprint + optional HMAC-SHA256 signature; tamper-evident offline | Signature requires external key management; unsigned certs provide integrity only |
| Art. 12 §2 | Logging — traceability | `issued_at`, `run_id`, `cert_id` | Unique IDs + ISO-8601 timestamp tie the cert to a specific point-in-time proof run | Does not include operator identity — add `--signing-key` for authorship |
| Art. 13 §3 | Transparency — instructions for use | `divergences_json[].claim_a`, `.claim_b`, `.repro_steps` | Human-readable description of each divergence, spec claim vs. observed behavior, reproduction steps | Natural language; not yet machine-processable by regulators without cherenkov tooling |
| Art. 15 §1 | Accuracy over lifecycle | `issued_at`, `subject.spec_hash` | Timestamps and spec hash enable detection of spec drift after issuance | Certificate does not re-validate automatically; re-run `cherenkov certify` on spec change |

---

## SOC 2 Type II — Trust Services Criteria (AICPA 2022)

| Criterion | Title | Cert field(s) | Evidence provided | Gap |
|---|---|---|---|---|
| CC4.1 | COSO Principle 9 — Identifies and analyzes risk | `verdict`, `summary`, `divergences_json` | Documented output of automated risk analysis (spec↔impl drift) | Not a substitute for risk-treatment decisions |
| CC5.2 | Logical-access authorization controls | `run_id`, `cert_id`, `issued_at` | Unique, time-stamped audit trail per verification run | Authorship attribution requires signing key |
| CC6.7 | Transmission integrity | `fingerprint`, `signature` | SHA-256 fingerprint prevents undetected modification in transit | HMAC key must be managed per key-management policy |
| CC7.2 | Evaluates and communicates deficiencies | `summary`, `divergences_json[].severity` | Structured, severity-classified deficiency list with evidence | Remediation workflow not included; use CI gate (`--fail-on-fail`) to block promotion |
| CC9.2 | Risk assessment of vendor/supplier | `subject.base_url`, `subject.spec_hash`, `verdict` | Point-in-time conformance record for a third-party API | Continuous coverage requires scheduled `cherenkov certify` runs |
| A1.2 (Availability) | System monitoring | `issued_at` (frequency) | Timestamped records enable trend analysis of conformance over time | No built-in scheduling; use CI cron or `cherenkov daemon` |

---

## ISO/IEC 25010:2023 — SQuaRE Product Quality

| Quality characteristic | Sub-characteristic | Cert field(s) | Evidence |
|---|---|---|---|
| 4.2.2 Functional suitability | Functional completeness | `verdict` = PASS/WARN/FAIL | Binary (or graded) statement of spec↔impl agreement |
| 4.2.5 Functional correctness | Functional correctness | `divergences_json[].claim_a` vs `.claim_b` | Side-by-side spec claim vs. observed behavior per endpoint |
| 4.2.8 Reliability | Fault tolerance | `summary.high`, `summary.critical` | Count of HIGH/CRITICAL severity faults found |
| 4.2.3 Performance efficiency | (supporting evidence) | `issued_at`, `run_id` | Links to the proof-run timing data if run-level metrics are emitted |
| 4.2.6 Maintainability | Modifiability risk | `subject.spec_hash` | Hash of the spec version under test; detects unapproved spec changes |
| 4.2.9 Security | Integrity | `fingerprint`, `signature` | Tamper-evidence of the quality record itself |

---

## Usage in an audit

To satisfy an audit request (EU AI Act technical documentation or SOC 2 evidence package):

1. **Issue** a certificate at each release gate:
   ```
   cherenkov certify --url https://api.example.com --spec openapi.json \
     --signing-key $CHERENKOV_CERT_KEY --output cert-$(date +%Y%m%d).json
   ```

2. **Archive** the cert JSON alongside the release artifact (git tag, S3, artifact registry).

3. **Verify** offline at any time:
   ```
   cherenkov certify --verify cert-20260627.json --signing-key $CHERENKOV_CERT_KEY
   ```

4. **Reference** specific fields in your technical documentation using the mapping table
   above, citing `cert_id` and `issued_at` as the traceability anchor.

---

## ISO/IEC 42001:2023 — AI management systems

The certificate serves as measurement evidence *into* an AIMS (it does not certify the
AIMS itself). Provision references use the ISO harmonized management-system structure.

| Clause | Requirement | Certificate fields | Notes |
|---|---|---|---|
| Cl. 9.1 | Monitoring, measurement, analysis and evaluation | `verdict`, `summary`, `issued_at`, `run_id` | Automated, timestamped measurement record of AI-adjacent API behaviour. |
| Cl. 10.2 | Nonconformity and corrective action | `divergences_json` | Each divergence carries claim_a/claim_b + repro steps enabling corrective action and re-verification. |

## OWASP AI Testing Guide v1 (2025)

Mapped to the guide's core evidence requirements (descriptive — the guide is a
methodology, not a numbered-controls standard):

| Requirement | Certificate fields | Notes |
|---|---|---|
| Repeatable trustworthiness evidence | `divergences_json`, `fingerprint` | Findings are third-party re-runnable; the record is SHA-256 tamper-evident. |
| Oracle integrity | `verdict`, `summary` | Oracles are spec-derived (status codes, documented fields/headers), never model output. Integrity of AI-*generated* suites is evidenced by `cherenkov check-suite`, complementary to this certificate. |

---

## OWASP Top 10 for LLM Applications (2025)

Numbered risk categories — distinct from the methodology-level "OWASP AI Testing
Guide" above. Only categories with an actual operational control in this repo are
claimed; the rest (LLM03 Supply Chain, LLM04 Data/Model Poisoning, LLM07-LLM10) are
intentionally omitted rather than force-mapped.

| Risk | Title | Certificate fields | What the repo provides | Gap / caveat |
|---|---|---|---|---|
| LLM01 | Prompt Injection | `verdict` | `cherenkov/adversarial/injector.py` + `detector.py` probe and scan generated test code for prompt-injection payloads and markers (role-hijack, instruction-override, spec-manipulation) | Adversarial pass rate is a separate report (`.cherenkov/adversarial_report.json`), not yet a certificate field |
| LLM02 | Sensitive Information Disclosure | — | `cherenkov/security/redact.py` scrubs API keys, bearer tokens, and PII from traces, logs, and agent memory before persistence | Applied at write-time; does not retroactively scrub existing records |
| LLM05 | Improper Output Handling | — | `cherenkov/adversarial/detector.py` scans AI-generated test code for unsafe constructs (eval, child_process, exec, exfiltration beacons) before it is trusted or executed | Pattern-based detection, not sandboxed execution |
| LLM06 | Excessive Agency | — | `cherenkov/hitl/` gates automated actions (e.g. auto-heal dispatch) behind a human-review queue with a PENDING/APPROVED/REJECTED state machine | Covers the auto-heal/repair paths; not every agentic action surface |

---

## Limitations (honesty clause)

The CHERENKOV Certificate is **not**:
- A full security audit
- A guarantee of zero bugs (coverage is bounded by the proof-run scope)
- A legal opinion on regulatory compliance

It is evidence of **systematic, reproducible, tamper-evident** conformance checking
at a point in time — a component of compliance, not a substitute for it.
