import { client } from '../client';
import { test, expect } from '@playwright/test';
test('post /users happy_path', async () => {
  const { data, response } = await client.POST('/users', { body: { email: 'x@y.com', password: 'Abc123!', name: 'X' } });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
});
