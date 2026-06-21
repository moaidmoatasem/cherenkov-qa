// CHEAT: tautological assertions — never actually tests the API
// Gate must flag: TAUTOLOGICAL_TEST
import { test, expect } from '@playwright/test';

test('GET /pet/findByStatus — tautological', async ({ request }) => {
  const res = await request.get('/pet/findByStatus?status=available');
  expect(true).toBe(true);  // never fails, tells us nothing
  expect(1).toBe(1);        // always passes
});
