---
last_updated: 2026-06-07
source: stub/generated_tests/, tests/eject_fixtures/, stub/target_spec.json
scope: Test generation patterns used by CHERENKOV across generated and ejected test suites
---

# Test Patterns

## Generated Tests (`stub/generated_tests/`)

### Happy Path (POST /users -> 201)

```typescript
import { client } from '../client';
import { test, expect } from '@playwright/test';

test('happy_path', async () => {
    const body = { email: 'test@example.com', password: 'password123' };
    const { response, data } = await client.POST('/users', { body });
    expect(response.status).toBe(201);
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('email');
});
```

### Validation Failure (password_too_short -> 422)

```typescript
test('password_too_short', async () => {
    const body = { email: 'test@example.com', password: 'short' };
    const { response } = await client.POST('/users', { body });
    expect(response.status).toBe(422);
});
```

### Visual Regression Baseline

```typescript
import { test, expect } from '@playwright/test';

test('visual regression baseline UI', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto(process.env.API_URL || 'http://127.0.0.1:8000/');
  await expect(page).toHaveScreenshot('baseline.png');
});
```

### K6 Performance Script

```javascript
export const options = {
  vus: 5,
  duration: '3s',
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.05'],
  },
};
export default function () {
  const res = http.post(url, payload, params);
  check(res, { 'status is 201': (r) => r.status === 201 });
  sleep(0.1);
}
```

## Ejected Test Fixtures (`tests/eject_fixtures/`)

Anti-lock-in verified: **zero CHERENKOV imports** - vanilla Playwright + openapi-fetch.

### Happy Path (ejected)

```typescript
import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user happy path returns 201 with id', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: 'test@example.com', password: 'longenough123' }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
  expect(data?.email).toBe('test@example.com');
});
```

### Validation Failure (ejected, annotated)

```typescript
// NOTE: this spec asserts 422 (the OpenAPI-declared validation status). The
// target API normalizes validation errors to 400, so this test is EXPECTED to
// go RED against the live target - it is the canonical "catches a status
// conformance bug" example.
```

## Common Patterns

| Pattern | Library | Convention |
|---------|---------|------------|
| HTTP client | `openapi-fetch` | `const { response, data } = await client.<METHOD>(path, options)` |
| Test framework | `@playwright/test` | `test/expect` syntax |
| Status assertion | Standard | `expect(response.status).toBe(NNN)` |
| Body shape assertion | Standard | `expect(data).toHaveProperty('key')` |
| Eject output | Standalone | Zero CHERENKOV references, self-contained types |

## Scoring Metadata

Generated tests scored on: `uses_openapi_fetch_client`, `no_forbidden_http`, `asserts_specific_status`, `asserts_body_shape`, `would_fail_on_wrong_output`, `compiles_likely`, `meaningful`.

Ejected fixtures: all 7/7 scoring criteria pass.

---

*Cross-ref: [endpoints.md](endpoints.md) for endpoint definitions, [known-bugs.md](known-bugs.md) for the 422-vs-400 pattern this code catches*
