import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /orders missing_user_id - returns 422', async () => {
  const { data, error, response } = await client.POST('/orders', {
    body: { product_id: 1, quantity: 1 } as any
  });
  expect(response.status).toBe(422);
  expect(error ?? data).toBeTruthy();
  expect((error as any)?.detail ?? (data as any)?.detail ?? (data as any)?.message).toBeTruthy();
});
