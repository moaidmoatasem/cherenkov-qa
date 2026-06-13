import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /users happy_path - creates user with 201 and id field', async () => {
  const { data, response } = await client.POST('/users', {
    body: {
      email: 'happy@cherenkov.dev',
      password: 'SecurePass1!',
      name: 'Happy Path User'
    }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
  expect(data).not.toHaveProperty('password_hash');
});
