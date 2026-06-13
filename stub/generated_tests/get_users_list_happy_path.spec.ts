import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /users happy_path - returns non-empty list after creation (BUG-3)', async () => {
  // Create a user first so the list is guaranteed non-empty
  const { response: cr } = await client.POST('/users', {
    body: { email: 'listusers@cherenkov.dev', password: 'ListPass99!', name: 'List Test' }
  });
  expect(cr.status).toBeLessThan(300);

  // BUG-3: regression mode always returns [] regardless of stored users
  const { data, response } = await client.GET('/users');
  expect(response.status).toBe(200);
  expect(Array.isArray(data)).toBe(true);
  expect((data as any[]).length).toBeGreaterThan(0);
});
