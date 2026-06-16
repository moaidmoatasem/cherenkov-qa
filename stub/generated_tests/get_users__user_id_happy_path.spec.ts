import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /users/{user_id} happy_path - no password_hash leakage (BUG-2)', async () => {
  const { data: created, response: cr } = await client.POST('/users', {
    body: {
      email: `get_${Date.now()}@cherenkov.dev`,
      password: 'TestPass99!',
      name: 'Get Test'
    }
  });
  expect(cr.status).toBeLessThan(300);
  const userId = (created as any).id ?? (created as any).user_id;

  const { data, response } = await client.GET('/users/{user_id}', {
    params: { path: { user_id: userId } }
  });
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
  expect((data as any).id).toBe(userId);
  expect(data).toHaveProperty('email');
  expect(data).toHaveProperty('name');
  expect(data).not.toHaveProperty('password_hash');
});
