import { client } from '../client';
import { test, expect } from '@playwright/test';

/**
 * GOLDEN FIXTURE: Correct spec-derived test for GET /pets.
 *
 * Expected bench result: all static gates PASS, verdict AUTO_APPROVE or HITL.
 * Gate 4 (assertion) passes because:
 *   - Status: expect(response.status).toBe(200)
 *   - Body shape: expect(data[0]).toHaveProperty('id')
 */
test('get /pets happy_path — lists pets with 200 and returns id + name', async () => {
  const { data, response } = await client.GET('/pets', {});
  expect(response.status).toBe(200);
  expect(Array.isArray(data)).toBe(true);
  if (data && data.length > 0) {
    expect(data[0]).toHaveProperty('id');
    expect(data[0]).toHaveProperty('name');
  }
});
