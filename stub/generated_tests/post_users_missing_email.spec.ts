import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /users missing_email - returns 422', async () => {
  const { data, response } = await client.POST('/users', {
    body: { password: 'password123', name: 'Test User' } as any
  });
  expect(response.status).toBe(422);
  expect(data).toBeTruthy();
  expect((data as any).detail ?? (data as any).message ?? (data as any).error).toBeTruthy();
});
