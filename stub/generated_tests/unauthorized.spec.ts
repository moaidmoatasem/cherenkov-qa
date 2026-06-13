import { client } from '../client';
import { test, expect } from '@playwright/test';

const _body = {
  "email": "test@cherenkov.dev",
  "password": "Password123!"
};

test('post /users happy_path happy_path', async () => {
  const { data, response } = await client.POST('/users', { body: _body });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
});
