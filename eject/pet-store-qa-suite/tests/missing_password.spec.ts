import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user missing_password - returns 422', async () => {
  const { error, response } = await client.POST('/users', {
    body: { email: 'test@example.com' } as any
  });
  expect(response.status).toBe(422);
  expect(error).toBeTruthy();
  expect((error as any).detail).toBeTruthy();
});