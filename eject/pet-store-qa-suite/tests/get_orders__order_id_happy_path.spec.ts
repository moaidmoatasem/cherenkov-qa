import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /orders/{order_id} happy_path - returns order details', async () => {
  const { data: user, response: ur } = await client.POST('/users', {
    body: {
      email: `getorder_${Date.now()}@cherenkov.dev`,
      password: 'TestPass99!',
      name: 'Order Reader'
    }
  });
  expect(ur.status).toBeLessThan(300);
  const userId = (user as any).id ?? (user as any).user_id;

  const { data: order, response: or2 } = await client.POST('/orders', {
    body: { user_id: userId, product_id: 2, quantity: 1 }
  });
  expect(or2.status).toBe(201);
  const orderId = (order as any).id;

  const { data, response } = await client.GET('/orders/{order_id}', {
    params: { path: { order_id: orderId } }
  });
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
  expect((data as any).id).toBe(orderId);
  expect(data).toHaveProperty('total_price');
  expect(data).toHaveProperty('user_id');
  expect(data).toHaveProperty('quantity');
  expect((data as any).user_id).toBe(userId);
  expect((data as any).quantity).toBe(1);
  expect(typeof (data as any).total_price).toBe('number');
  expect((data as any).total_price).toBeGreaterThan(0);
});
