import { client } from '../client';
import { test, expect } from '@playwright/test';

test('delete /users/{user_id} happy_path - deletes user with 204', async () => {
  const { data: created, response: cr } = await client.POST('/users', {
    body: {
      email: `delete_${Date.now()}@cherenkov.dev`,
      password: 'TestPass99!',
      name: 'To Delete'
    }
  });
  expect(cr.status).toBeLessThan(300);
  const userId = (created as any).id ?? (created as any).user_id;

  const { response } = await client.DELETE('/users/{user_id}', {
    params: { path: { user_id: userId } }
  });
  expect(response.status).toBe(204);

  // Verify the user is actually gone
  const { response: getResponse } = await client.GET('/users/{user_id}', {
    params: { path: { user_id: userId } }
  });
  expect(getResponse.status).toBe(404);
});
