# Test Patterns

Generated test patterns and common mutation scenarios produced by CHERENKOV's GENERATE stage.
Source: `stub/generated_tests/*.spec.ts`

## Happy Path Pattern (P1)

```typescript
import { test, expect } from '@playwright/test';
import createClient from '../client';

test('POST /users happy path', async () => {
  const client = createClient();
  const { data, response } = await client.POST('/users', {
    body: { email: 'test@example.com', password: 'password123' }
  });
  expect(response.status).toBe(201);
  expect(data).toBeDefined();
  expect(data.email).toBe('test@example.com');
});
```

## Validation Error Pattern (P2)

```typescript
test('POST /users password too short', async () => {
  const client = createClient();
  const { response } = await client.POST('/users', {
    body: { email: 'test@example.com', password: 'short' }
  });
  expect(response.status).toBe(422);  // spec-derived
});
```

## Client Usage Rules
- Must use `openapi-fetch` `createClient()` — no `fetch()` or `axios`
- Import path: `'../client'`
- Response destructuring: `const { data, error, response } = await client.<METHOD>(...)`
- Status assertions use spec-derived values (never hardcoded)

## Mutation Categories

| Category | Pattern | Expected Status |
|----------|---------|-----------------|
| happy_path | Valid request body | 200/201 |
| validation_error | Invalid field constraints | 422 (spec-derived) |
| edge_case | Boundary values | 422 or 400 |
| auth_no_token | Missing auth header | 401 |
| auth_invalid_token | Malformed auth token | 401 |
| dast_sqli | SQL injection payload | 400/422 (safe reject) |
| dast_xss | XSS payload | 400/422 (safe reject) |

## Assertion Patterns
- `expect(response.status).toBe(<spec-derived>)` — status check
- `expect(data).toBeDefined()` — response body exists
- `expect(data.<field>).toBe(<value>)` — field-level assertion (suggested by validate)
- `request_body` vs `response_body` comparison — tightening suggestions

## Cross-references
- See `endpoints.md` for endpoint schemas
- See `known-bugs.md` for conformance drift patterns (e.g., 422 vs 400)
