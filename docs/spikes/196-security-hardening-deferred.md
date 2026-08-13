# Capture #196 — Security Hardening: HITL Auth + At-Rest Encryption (DEFERRED)

**Issue:** [#196](https://github.com/moaidmoatasem/cherenkov-qa/issues/196) · `[Horizon V][backlog][deferred]`
**Source:** teammate Doc2 (marked **P0 there**)
**Status:** **DE-PRIORITIZED — captured, not a launch blocker.** Do **not** treat
as a gate item now.
**Related:** [Scope Ledger — the fabricated validation gate](../SCOPE_LEDGER.md) (the
shipping blocker at the time this was captured; the gate has since been recorded as
passed per owner decision, 2026-06-08). The companion note on the OpenCLAW integration
this capture also cited was never written — see the note at the bottom of this file.

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
   Note: this capture asserted the HITL *backend itself* is still nascent, citing
   an OpenCLAW integration review — auth should be designed in as that backend is
   built for hosting, not bolted on after. **That premise is unverified and is
   contradicted by the evidence in the tree** (see the note below).
2. **At-rest encryption** — the SQLite store (`cherenkov/hitl/store.py`) holds
   review/feedback state in plaintext on disk. Hosted/multi-tenant = encrypt at
   rest (SQLCipher or equivalent) + key management.

## Acceptance (per issue)

> Revisited when multi-user/hosted deployment is on the roadmap.

No code change now. This capture doc **is** the deliverable: the requirement is
recorded, the deferral rationale is explicit, and the re-open trigger is
defined. Anchor launch status to `docs/HANDOVER.md` and the validation gate —
**not** to this item.

---

## Resolved: both asks are implemented — this capture is stale (2026-08-13)

This document says **DEFERRED**, *"no code change now"*, and *"do not treat as a gate item"*.
Both of its asks have since shipped, and the code cites this issue by number.

**1. HITL auth — done.** `cherenkov/web/routes/review_routes.py`:

```python
@router.post("/api/v1/review/approve")
async def approve_review_item(payload, _auth=Depends(verify_api_key),
                              _role=Depends(require_role(Role.reviewer))):
```

Approve and reject both require an API key *and* the reviewer role. Precisely:
`require_role` returns early when `AUTH_ENABLED` is false
(`cherenkov/web/auth/deps.py`), so enforcement is conditional on that setting — which is
the localhost-first default this document argued for, with the authz designed in rather
than bolted on.

**2. At-rest encryption — done.** `cherenkov/hitl/store.py`, line 13, naming this issue:

> `[Issue #196] At-rest encryption: set CHERENKOV_DB_KEY to enable SQLCipher-based`
> `encryption. Falls back to plain SQLite if pysqlcipher3 is not available.`

**And the premise was wrong even when written.** The re-open criteria below rest on the
HITL backend being nascent. It is 743 lines (`store.py` 344, `cmd.py` 274,
`contracts.py` 101), and `docs/vision/11_CONSOLIDATION_AUDIT.md` — dated *before* this
capture — records it as *"atomic queue + `hitl/v1` envelope, race-proven"* with
*"atomic SQL gatekeeper, race-proven 10/10 + 5/5"*.

Nothing above has been edited: this is a dated capture and rewriting it would destroy the
record. But it should not be read as current status. Found via `cherenkov brain`, which
flagged the dangling citation below and led here.

## Note on a citation that never existed (2026-08-13)

This capture originally cited a wikilink, `openclaw-integration-review`, twice —
once as *"no HITL backend exists yet"* and once for *"the HITL backend itself is
still nascent"*. **No such document has ever existed in this repository.** The
links were found by `cherenkov brain findings` and are left unresolved here
rather than repointed, because no document in the tree substitutes for them —
and, more importantly, because the evidence in the tree contradicts the claim
they were cited to support:

> `docs/vision/11_CONSOLIDATION_AUDIT.md` (2026-06-04), line 27:
> `` | `hitl/` | 442 | ✅ atomic queue + `hitl/v1` envelope, race-proven | ``
> and line 57: *"HITL concurrency: atomic SQL gatekeeper, race-proven 10/10 + 5/5."*

Either this capture's premise is wrong, or the Consolidation Audit is — and the
deferral rationale above rests partly on that premise. Someone with the history
should reconcile the two before this issue is re-opened. Inventing a citation to
make the link resolve would have buried the discrepancy instead of surfacing it.
