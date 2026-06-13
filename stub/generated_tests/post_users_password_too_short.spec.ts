import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /users password_too_short - returns 422', async () => {
  const { response } = await client.POST('/users', {
    body: { email: 'test@cherenkov.dev', password: 'short', name: 'Test User' }
  });
  expect(response.status).toBe(422);
});
