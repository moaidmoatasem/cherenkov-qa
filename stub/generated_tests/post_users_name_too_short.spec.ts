import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /users name_too_short - returns 422', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: 'test@cherenkov.dev', password: 'password123', name: '' }
  });
  expect(response.status).toBe(422);
  expect(data).toBeTruthy();
  expect((data as any).detail ?? (data as any).message ?? (data as any).error).toBeTruthy();
});
