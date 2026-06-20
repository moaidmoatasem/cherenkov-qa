import { client } from '../client';
import { test, expect } from '@playwright/test';

test('patch /users/{user_id} happy_path - updates user name', async () => {
  const { data: created, response: cr } = await client.POST('/users', {
    body: {
      email: `patch_${Date.now()}@cherenkov.dev`,
      password: 'TestPass99!',
      name: 'Before Patch'
    }
  });
  expect(cr.status).toBeLessThan(300);
  const userId = (created as any).id ?? (created as any).user_id;

  const { data, response } = await client.PATCH('/users/{user_id}', {
    params: { path: { user_id: userId } },
    body: { name: 'After Patch' }
  });
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
  expect((data as any).id).toBe(userId);
  expect(data).toHaveProperty('email');
  expect((data as any).name).toBe('After Patch');
  expect(data).not.toHaveProperty('password_hash');
});
