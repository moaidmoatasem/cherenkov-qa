import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user happy path', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: `happy_${Date.now()}@example.com`, password: 'password123', name: 'Happy User' }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
});
