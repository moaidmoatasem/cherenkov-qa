import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /users name_too_short - returns 422', async () => {
  const { response } = await client.POST('/users', {
    body: { email: 'test@cherenkov.dev', password: 'password123', name: '' }
  });
  expect(response.status).toBe(422);
});
