# Spike #194 — Lightweight DAST Mutation Profile

**Issue:** [#194](https://github.com/moaidmoatasem/cherenkov-qa/issues/194) · `[Horizon V][9c][spike]` · Source: Doc3 B / F7
**Status:** Spike (design + prototype). Implementation deferred to Phase 3+.
**Related:** [[fabricated-validation-gate]] (validation gate is the gating milestone before this lands)

## Goal

Add a **security** profile to the ingest mutation menu that injects OWASP-style
payloads (SQLi / XSS strings) and asserts the server *safely rejects* them —
no `500`, no reflected/executed payload. This is a natural extension of the
existing deterministic 400/422 boundary-mutation testing, not a new engine.

## Where it plugs in

The mutation menu is built deterministically in
[`cherenkov/stages/ingest.py`](../../cherenkov/stages/ingest.py) per endpoint
(`happy_path`, `auth`, and per-field `validation` cases). Each is a
`Mutation` contract ([`cherenkov/core/contracts.py:59`](../../cherenkov/core/contracts.py)):

```python
class Mutation(BaseModel):
    id: str
    case_type: str          # currently: "validation" | "happy_path" | "auth"
    expected_status: int
    instruction: str        # given verbatim to the generator
    value: object | None = None
```

The security profile adds a **new `case_type = "security"`**, emitted only for
`string`-typed body/query properties (the injectable surface). No change to the
generate/review pipeline is required — the generator already consumes
`instruction` verbatim and the reviewer already scores assertion quality.

## Payload set (spike definition)

Keep it *lightweight* — a fixed, curated set, not a fuzzing campaign. One
representative payload per class is enough to prove the safe-rejection contract.

| Class | Payload (example) | Injected into |
|-------|-------------------|---------------|
| SQLi (tautology) | `' OR '1'='1` | any string field |
| SQLi (stacked) | `'; DROP TABLE users;--` | any string field |
| XSS (reflected) | `<script>alert(1)</script>` | any string field |
| XSS (attribute) | `" onmouseover="alert(1)` | any string field |
| Path traversal | `../../../../etc/passwd` | path/query string params |
| Template injection | `${{7*7}}` | any string field |

These live as a module-level constant (e.g. `DAST_PAYLOADS` in `ingest.py`) so
the set is auditable and version-controlled.

## Expected-safe assertions

A security mutation passes when the server **rejects safely**. The reviewer's
`asserts_specific_status` gate maps onto this directly:

1. **Status:** response is `4xx` (typically `400`/`422`, the same
   `validation_status` already computed at `ingest.py:103`) — explicitly **not**
   `5xx` and **not** `2xx`.
2. **No reflection:** the response body does **not** contain the payload
   verbatim (catches reflected XSS / error-leak of the injected string).
3. **No execution side-effect:** for `${{7*7}}`-style template payloads, the
   body must not contain the evaluated result (`49`).

Generated spec shape (mirrors the existing `password_too_short.spec.ts` fixture):

```ts
test('SQLi tautology in email is safely rejected', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: "' OR '1'='1", password: 'longenough123' }
  });
  expect(response.status).toBeGreaterThanOrEqual(400);
  expect(response.status).toBeLessThan(500);              // no 500 / crash
  expect(JSON.stringify(data ?? '')).not.toContain("' OR '1'='1");  // no reflection
});
```

## Prototype (additive, ~20 LOC in ingest.py)

```python
DAST_PAYLOADS = [
    ("sqli_tautology", "' OR '1'='1"),
    ("xss_script", "<script>alert(1)</script>"),
    ("path_traversal", "../../../../etc/passwd"),
    ("template_injection", "${{7*7}}"),
]

# inside the `for prop, prop_schema in properties.items()` loop, string branch:
if prop_schema.get("type") == "string":
    for pid, payload in DAST_PAYLOADS:
        mutations.append(Mutation(
            id=f"{prop}_{pid}",
            case_type="security",
            expected_status=validation_status,   # 4xx; reviewer also asserts < 500
            instruction=(
                f"Set '{prop}' to the literal hostile payload {payload!r}. "
                f"Assert the response status is 4xx (NOT 5xx, NOT 2xx) and that "
                f"the response body does NOT echo the payload verbatim."
            ),
            value=payload,
        ))
```

## Acceptance check (per issue)

- ✅ Payload set defined (table above, curated/auditable).
- ✅ Expected-safe assertions defined (4xx-not-5xx + no-reflection + no-eval).
- ✅ Prototype sketched against the target API (`POST /users`, string field
  `email`) — runs through the *existing* generate→review→eject path unchanged.

## Risks / open questions

- **Opt-in only.** Security mutations should be behind a profile flag
  (`--profile security` / config toggle) so default runs stay focused on
  conformance. Injecting 4–6 extra cases per string field on a large spec
  (Stripe) would balloon the menu otherwise — ties into [[195 chunking spike]].
- **False reds on legitimate echo.** APIs that legitimately store-and-return a
  field (e.g. a `description`) will "reflect" the payload. The no-reflection
  assertion needs a per-endpoint allowlist, or should be downgraded to a
  warning when `expected_status` is itself a 2xx-storing endpoint.
- **Not a replacement for real DAST** (ZAP/Burp). This is a *smoke-level*
  safety contract that rides the existing deterministic harness — scope it as
  such in docs to avoid over-promising.
