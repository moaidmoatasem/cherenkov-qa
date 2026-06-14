import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /users missing_password - returns 422', async () => {
  const { response } = await client.POST('/users', {
    body: { email: 'test@cherenkov.dev', name: 'Test User' } as any
  });
  expect(response.status).toBe(422);
});
