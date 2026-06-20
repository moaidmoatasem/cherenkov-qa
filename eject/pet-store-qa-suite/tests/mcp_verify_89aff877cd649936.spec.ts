import { client } from '../client';
import { test, expect } from '@playwright/test';
test('cheat test', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: `cheat_${Date.now()}@y.com`, password: 'Abc12345!', name: 'Cheat User' }
  });
  expect(response.status).toBeLessThan(500);
  expect(data).toHaveProperty('id');
});
