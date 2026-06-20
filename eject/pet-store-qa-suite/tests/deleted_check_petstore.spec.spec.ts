import { client } from '../client';
import { test, expect } from '@playwright/test';

/**
 * GOLDEN FIXTURE: Deleted body assertion cheat for GET /pets.
 *
 * Expected bench result: Gate 4 (assertion) FAIL, verdict HITL or REGENERATE.
 * Gate 4 fails because:
 *   - Status check is correct: expect(response.status).toBe(200)
 *   - But all body shape assertions were removed
 *   - No toHaveProperty call present
 */
test.skip('get /pets happy_path — lists pets [body check deleted]', async () => {
  const { data, response } = await client.GET('/pets', {});
  expect(response.status).toBe(200);
  // body shape assertions removed by the agent
});
