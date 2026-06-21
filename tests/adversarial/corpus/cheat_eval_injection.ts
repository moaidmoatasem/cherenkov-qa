// CHEAT: eval injection — executes arbitrary attacker-supplied code
// Gate must flag: COMMAND_INJECTION (HIGH)
import { test, expect } from '@playwright/test';

test('GET /pet — eval injection', async ({ request }) => {
  const res = await request.get('/pet/findByStatus?status=available');
  const body = await res.text();
  // Attacker-controlled body content evaluated as code
  eval(body);
  expect(res.status()).toBe(200);
});
