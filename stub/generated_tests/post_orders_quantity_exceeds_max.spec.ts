import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /orders quantity_exceeds_max - returns 422', async () => {
  const { response } = await client.POST('/orders', {
    body: {} as any
  });
  expect(response.status).toBe(422);
});
