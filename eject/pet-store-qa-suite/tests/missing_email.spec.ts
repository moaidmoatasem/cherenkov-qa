import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user missing_email - returns 422', async () => {
  const { error, response } = await client.POST('/users', {
    body: { password: 'password123' } as any
  });
  expect(response.status).toBe(422);
  expect(error).toBeTruthy();
  expect((error as any).detail).toBeTruthy();
});