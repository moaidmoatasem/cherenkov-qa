import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user happy path returns 201 with id', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: 'test@example.com', password: 'longenough123' }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
  expect(data?.email).toBe('test@example.com');
});
