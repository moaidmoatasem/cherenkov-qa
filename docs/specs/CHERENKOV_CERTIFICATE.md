# Spec — The CHERENKOV Certificate

> **Status:** DRAFT (design-ready, build-gated on Phase 1+2). Owner: TBD.
> **Why:** the artifact that turns a tool into a standard — portable, signed, verifiable proof of what software actually does vs. claims. See [../NORTH_STAR.md](../NORTH_STAR.md) §3 (Rung 3), [../ROADMAP_AQE.md](../ROADMAP_AQE.md) Phase 3.
> **Date:** 2026-06-16

## 1. What it is
A signed, machine-verifiable, human-readable record asserting: *"At time T, system/suite X, at content-hash H, was verified by CHERENKOV engine vE and found to conform to its declared sources of truth with result R, including these integrity checks."* Think SSL cert / SOC2 report, but **live, granular, and self-verifying** — and crucially, **it states what was NOT verified**, so it can never overclaim.

## 2. Design principles
- **Forgeable by no one, verifiable by anyone.** Cryptographic signature; offline verification.
- **Honest by construction.** Explicit scope: what was checked, what wasn't, confidence. No green badge without a verdict behind it.
- **Neutral.** No model-vendor dependency; the spec is open so others can verify (and even issue) without us.
- **Portable.** A single file you can forward to a teammate, buyer, auditor, or CI gate.
- **Tamper-evident & reproducible.** The cert binds to content hashes; re-running the engine on the same inputs reproduces the verdict.

## 3. Structure (JWS / detached-signature over a canonical JSON payload)
```json
{
  "cert_version": "1.0",
  "subject": {
    "kind": "suite|system|release",
    "name": "string",
    "content_hash": "sha256:...",
    "vcs": { "repo": "", "commit": "" }
  },
  "claim": {
    "verdict": "verified|verified-with-warnings|failed",
    "sources_of_truth": ["openapi@hash", "asyncapi@hash", "traffic@hash"],
    "integrity": {
      "no_weakened_assertions": true,
      "no_deleted_checks": true,
      "no_hallucinated_oracles": true
    },
    "coverage": { "claimed": 0.0, "verified": 0.0 }
  },
  "scope": {
    "checked": ["conformance", "drift", "assertion-meaningfulness"],
    "NOT_checked": ["load", "security-pentest"],
    "confidence": "high|medium|low"
  },
  "evidence": { "report_id": "", "report_hash": "sha256:...", "reproduction_cmd": "" },
  "issuer": { "engine_version": "", "issued_at": "ISO-8601", "issuer_id": "key-fingerprint" },
  "validity": { "not_after": "ISO-8601|null", "revocation_url": "string|null" }
}
```
- **Signature:** detached JWS (Ed25519 default). The signed bytes are the RFC-8785 (JCS) canonicalization of the payload.
- **Binding:** `subject.content_hash` + `evidence.report_hash` make the cert worthless if either the artifact or the underlying report changes.

## 4. Issuance
- `cherenkov certify --from-report <id> --key <ref>` → emits `name.cherenkov-cert.json` (+ optional `.sig`).
- Keys: local dev key (self-signed, for personal use) → org key (team trust) → eventually a CHERENKOV root for the public authority (Phase 3.4+).
- Issuance is impossible without a passing/closed report — **you cannot certify what wasn't verified.**

## 5. Verification
- `cherenkov verify-cert <file>` → checks signature, recomputes canonical hash, optionally re-runs evidence to confirm reproducibility. Fully offline.
- Public endpoint (optional): `verify.cherenkov.*/c/<id>` renders a human page + machine JSON; never required for trust (offline path is canonical).
- **Revocation:** optional `revocation_url`; a cert can be marked stale if a source-of-truth or the engine is later found flawed.

## 6. The badge
- `![CHERENKOV verified](...)` reads the cert and renders verdict + scope + date. Clicking shows the *scope* (including NOT_checked) — honesty is the brand.
- A badge with no valid, current cert behind it renders as "unverified" — the badge can't lie.

## 7. Trust model / network effect
- v0: self-signed, personal confidence.
- v1: org-signed, team/CI gates ("merge if verified").
- v2: cross-org — one party (buyer, marketplace, regulator) *requires* a cert → counterparties need one → standard compounds.
- The spec is **open**: anyone can verify; independent issuers possible. Neutrality is the moat, not a closed format.

## 8. Threats & mitigations
- **Replay/overclaim:** content+report hash binding; scope always explicit.
- **Key compromise:** rotation + revocation + short validity for high-stakes certs.
- **"Verified theater":** scope mandates `NOT_checked` and confidence; coverage is `claimed` vs `verified` side-by-side.
- **Vendor capture:** open spec + offline verification means no one (including us) is a required intermediary.

## 9. Open questions
- Transparency log (Sigstore/Rekor-style) for public certs — yes eventually; overkill for v0?
- Granularity: per-release vs per-endpoint vs per-test certs (probably layered).
- Standards alignment: map fields to EU AI Act technical-documentation + SOC2 evidence early.

## 10. Acceptance (post Phase 1+2)
1. Issue a cert from a real report; tamper with the artifact → verification fails.
2. Verify fully offline; re-run evidence reproduces the verdict.
3. Badge renders verdict + scope and degrades to "unverified" with no valid cert.
4. A second implementation (independent) can verify our cert from the open spec.
