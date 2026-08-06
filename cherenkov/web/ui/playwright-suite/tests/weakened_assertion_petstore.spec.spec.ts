import { client } from '../client';
import { test, expect } from '@playwright/test';

/**
 * GOLDEN FIXTURE: Weakened assertion cheat for GET /pets.
 *
 * Expected bench result: Gate 4 (assertion) FAIL, verdict HITL or REGENERATE.
 * Gate 4 fails because the status check uses a loose range comparison
 * (toBeLessThan) instead of asserting a specific status code.
 */
test('get /pets happy_path — lists pets [weakened assertion]', async () => {
  const { data, response } = await client.GET('/pets', {});
  expect(response.status).toBeLessThan(500);
  if (data && data.length > 0) {
    expect(data[0]).toHaveProperty('id');
  }
});
