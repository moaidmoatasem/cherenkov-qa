import { client } from '../client';
import { test, expect } from '@playwright/test';

test('post /orders happy_path - creates order with 201', async () => {
  const { data: user, response: ur } = await client.POST('/users', {
    body: {
      email: `order_${Date.now()}@cherenkov.dev`,
      password: 'TestPass99!',
      name: 'Order User'
    }
  });
  expect(ur.status).toBeLessThan(300);
  const userId = (user as any).id ?? (user as any).user_id;

  const { data, response } = await client.POST('/orders', {
    body: { user_id: userId, product_id: 1, quantity: 2 }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
  expect(data).toHaveProperty('total_price');
  expect(data).toHaveProperty('user_id');
  expect(data).toHaveProperty('quantity');
  expect((data as any).user_id).toBe(userId);
  expect((data as any).quantity).toBe(2);
  expect(typeof (data as any).total_price).toBe('number');
  expect((data as any).total_price).toBeGreaterThan(0);
});
