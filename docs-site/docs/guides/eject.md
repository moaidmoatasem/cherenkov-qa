---
title: Eject to Vanilla Playwright
description: Use cherenkov eject to strip all CHERENKOV imports and produce standalone Playwright tests with zero lock-in.
---

# Eject to Vanilla Playwright

`cherenkov eject` is your **zero lock-in guarantee**. Run it at any time to strip all CHERENKOV dependencies from your generated tests, leaving pure, human-readable Playwright tests that run forever — with no CHERENKOV installed.

---

## Run the Eject Command

```bash
cherenkov eject --output ./my-tests
```

This takes every test in your CHERENKOV workspace and transforms it:

**Before (CHERENKOV test):**
```typescript
import { createCherenkovClient } from '@cherenkov/client';
import { validateResponse } from '@cherenkov/validate';

test('GET /pets returns 200', async ({ request }) => {
  const client = createCherenkovClient({ baseUrl: process.env.API_URL });
  const res = await client.get('/pets');
  validateResponse(res, petSchema);
  expect(res.status).toBe(200);
});
```

**After (ejected vanilla Playwright):**
```typescript
import createClient from 'openapi-fetch';
import type { paths } from './generated-types';

test('GET /pets returns 200', async ({ request }) => {
  const client = createClient<paths>({ baseUrl: process.env.API_URL });
  const { data, response } = await client.GET('/pets');
  expect(response.status).toBe(200);
  expect(data).toBeDefined();
});
```

---

## Run Ejected Tests

```bash
cd my-tests
npm install
npx playwright test

# All tests pass — no CHERENKOV required
```

---

## What Gets Removed

| Removed | Replaced With |
|---------|--------------|
| `@cherenkov/client` import | `openapi-fetch` (standard) |
| `@cherenkov/validate` import | Inline assertions |
| CHERENKOV-specific type helpers | Generated `openapi-typescript` types |
| CHERENKOV config file references | Standard Playwright config |

---

## What Stays

- Test logic and assertions — unchanged
- TypeScript type safety — via `openapi-fetch` + `openapi-typescript`
- Playwright fixtures and configuration
- Your `.env` and base URL configuration

---

## Eject Strategy

!!! tip "When to eject"
    - Before migrating to a new test framework
    - Before archiving a project
    - When handing tests to a team that doesn't use CHERENKOV
    - As a periodic "test ownership audit"

CHERENKOV recommends ejecting periodically to verify that your tests don't have hidden CHERENKOV dependencies.

---

## Verify Portability

```bash
# Confirm no CHERENKOV imports remain
grep -r "@cherenkov" ./my-tests
# Expected: no output

# Run without CHERENKOV installed
pip uninstall cherenkov-qa
cd my-tests && npx playwright test
# Expected: all tests pass
```
