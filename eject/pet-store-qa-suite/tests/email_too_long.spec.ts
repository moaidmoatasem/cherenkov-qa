import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user with email too long - returns 422', async () => {
  const { error, response } = await client.POST('/users', {
    body: { email: 'a'.repeat(51), password: 'password123' }
  });
  expect(response.status).toBe(422);
  expect(error).toBeTruthy();
  expect((error as any).detail).toBeTruthy();
});