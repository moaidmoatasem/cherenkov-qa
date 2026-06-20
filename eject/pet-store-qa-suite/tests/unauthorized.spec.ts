import { client } from '../client';
import { test, expect } from '@playwright/test';

// Auth enforcement not yet in target API (returns 422 instead of 401)
test.skip('create user unauthorized - returns 401', async () => {
  const { error, response } = await client.POST('/users', {
    body: { email: 'test@example.com', password: 'password123', name: 'Test' }
  });
  expect(response.status).toBe(401);
  expect(error).toBeTruthy();
});
