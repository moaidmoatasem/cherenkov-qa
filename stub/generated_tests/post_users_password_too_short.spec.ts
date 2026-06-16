import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /users password_too_short - returns 422', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: 'test@cherenkov.dev', password: 'short', name: 'Test User' }
  });
  expect(response.status).toBe(422);
  expect(data).toBeTruthy();
  expect((data as any).detail ?? (data as any).message ?? (data as any).error).toBeTruthy();
});
