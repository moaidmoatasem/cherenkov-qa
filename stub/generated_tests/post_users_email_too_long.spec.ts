import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /users email_too_long - returns 422', async () => {
  const longEmail = 'a'.repeat(101) + '@example.com';
  const { response } = await client.POST('/users', {
    body: { email: longEmail, password: 'password123', name: 'Test User' }
  });
  expect(response.status).toBe(422);
});
