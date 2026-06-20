import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user with too short password - returns 422', async () => {
  const { error, response } = await client.POST('/users', {
    body: { email: 'test@example.com', password: 'pass' } as any
  });
  expect(response.status).toBe(422);
  expect(error).toBeTruthy();
  expect((error as any).detail).toBeTruthy();
});