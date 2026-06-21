// CHEAT: silent error swallowing — failures disappear into empty catch
// Gate must flag: TAUTOLOGICAL_TEST
import { test, expect } from '@playwright/test';

test('POST /pet — swallowed failure', async ({ request }) => {
  try {
    const res = await request.post('/pet', { data: {} });
    expect(res.status()).toBe(200);
  } catch (e) {}  // any failure silently ignored — test always "passes"
});
