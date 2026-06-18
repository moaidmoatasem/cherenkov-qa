import { client } from '../client';
import { test, expect } from '@playwright/test';
test('cheat test', async () => {
  const { data, response } = await client.POST('/users', { body: { email: 'x@y.com', password: 'Abc123!', name: 'X' } });
  expect(response.status).toBeLessThan(500);
  expect(data).toHaveProperty('id');
});
