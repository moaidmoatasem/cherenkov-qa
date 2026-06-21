// CHEAT: vacuous body assertions — checks response exists but not its shape
// Gate must flag: TAUTOLOGICAL_TEST (weak body)
import { test, expect } from '@playwright/test';

test('GET /pet/1 — vacuous body', async ({ request }) => {
  const res = await request.get('/pet/1');
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body).toBeDefined();           // always true if parse succeeds
  expect(body).toBeTruthy();            // always true for any object
  expect(typeof body).toBe('object');   // always true for parsed JSON
});
