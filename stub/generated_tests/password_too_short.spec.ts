import { client } from '../client';
import { test, expect } from '@playwright/test';

/**
 * DRIFT FIXTURE: demonstrates spec conformance failure detection.
 *
 * Sends a password that is too short (< 8 chars) and asserts 201.
 * The real API returns 422 (validation error), so this test always FAILs —
 * surfacing the conformance drift that CHERENKOV validate is designed to catch.
 */
test('post /users password_too_short — short password triggers validation error', async () => {
  const { data, response } = await client.POST('/users', {
    body: {
      email: 'test@example.com',
      password: 'abc',
    },
  });
  // Intentionally wrong expectation: real API returns 422 for short passwords
  expect(response.status).toBe(201);
});
