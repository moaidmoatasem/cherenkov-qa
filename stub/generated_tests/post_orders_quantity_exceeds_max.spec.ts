import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /orders quantity_exceeds_max - returns 422 when quantity is above maximum', async () => {
  const { data: user, response: ur } = await client.POST('/users', {
    body: {
      email: `qtymax_${Date.now()}@cherenkov.dev`,
      password: 'TestPass99!',
      name: 'Qty Max User'
    }
  });
  expect(ur.status).toBeLessThan(300);
  const userId = (user as any).id ?? (user as any).user_id;

  const { data, error, response } = await client.POST('/orders', {
    body: { user_id: userId, product_id: 1, quantity: 999999 }
  });
  expect(response.status).toBe(422);
  expect(error ?? data).toBeTruthy();
  expect((error as any)?.detail ?? (data as any)?.detail ?? (data as any)?.message).toBeTruthy();
});
