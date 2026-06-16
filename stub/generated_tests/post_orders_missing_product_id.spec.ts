import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /orders missing_product_id - returns 422', async () => {
  const { data: user, response: ur } = await client.POST('/users', {
    body: {
      email: `nopid_${Date.now()}@cherenkov.dev`,
      password: 'TestPass99!',
      name: 'No Product Id'
    }
  });
  expect(ur.status).toBeLessThan(300);
  const userId = (user as any).id ?? (user as any).user_id;

  // Send a body with user_id and quantity but no product_id
  const { data, response } = await client.POST('/orders', {
    body: { user_id: userId, quantity: 1 } as any
  });
  expect(response.status).toBe(422);
  expect(data).toBeTruthy();
  expect((data as any).detail ?? (data as any).message ?? (data as any).error).toBeTruthy();
});
