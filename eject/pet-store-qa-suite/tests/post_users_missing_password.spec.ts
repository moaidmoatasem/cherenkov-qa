import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /users missing_password - returns 422', async () => {
  const { data, error, response } = await client.POST('/users', {
    body: { email: 'test@cherenkov.dev', name: 'Test User' } as any
  });
  expect(response.status).toBe(422);
  expect(error ?? data).toBeTruthy();
  expect((error as any)?.detail ?? (data as any)?.detail ?? (data as any)?.message).toBeTruthy();
});
