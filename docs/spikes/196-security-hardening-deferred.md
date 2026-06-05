# Capture #196 — Security Hardening: HITL Auth + At-Rest Encryption (DEFERRED)

**Issue:** [#196](https://github.com/moaidmoatasem/cherenkov-qa/issues/196) · `[Horizon V][backlog][deferred]`
**Source:** teammate Doc2 (marked **P0 there**)
**Status:** **DE-PRIORITIZED — captured, not a launch blocker.** Do **not** treat
as a gate item now.
**Related:** [[fabricated-validation-gate]] (the real shipping blocker), [[openclaw-integration-review]] (no HITL backend exists yet)

## Why it is deferred (not dropped)

CHERENKOV is **localhost-first, single-user, pre-validation**. The two asks in
this issue — HITL authentication and SQLite at-rest encryption — only become
*real* threats once there is a **multi-user or hosted deployment**, which does
not exist today and will not exist until *after* the validation gate is passed
and an explicit scope decision is made to host.

Doc2 graded these P0 against an implied hosted/multi-tenant deployment model.
Against the *actual* current model (one operator, one machine, no network
exposure), the threat surface they close is not yet present. Shipping auth +
encryption now would be securing a door on a building that hasn't been built —
real engineering cost spent ahead of the risk it mitigates.

This file exists so the requirement is **not lost**, and so the P0/deferred
disagreement between Doc2 and the current roadmap is recorded with its
rationale.

## Scope when revisited

Trigger condition: **multi-user or hosted deployment lands on the roadmap.**
At that point, this issue should be re-opened and split into:

1. **HITL auth** — the human-in-the-loop review/approval surface
   (`cherenkov/hitl/`) currently trusts the local operator implicitly. Hosted =
   needs authn/authz on review actions (who approved this diff? who can eject?).
   Note: per [[openclaw-integration-review]], the HITL *backend itself* is still
   nascent — auth should be designed in as that backend is built for hosting,
   not bolted on after.
2. **At-rest encryption** — the SQLite store (`cherenkov/hitl/store.py`) holds
   review/feedback state in plaintext on disk. Hosted/multi-tenant = encrypt at
   rest (SQLCipher or equivalent) + key management.

## Acceptance (per issue)

> Revisited when multi-user/hosted deployment is on the roadmap.

No code change now. This capture doc **is** the deliverable: the requirement is
recorded, the deferral rationale is explicit, and the re-open trigger is
defined. Anchor launch status to `docs/HANDOVER.md` and the validation gate —
**not** to this item.
