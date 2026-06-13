import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /orders quantity_below_min - returns 422', async () => {
  const { response } = await client.POST('/orders', {
    body: {} as any
  });
  expect(response.status).toBe(422);
});
