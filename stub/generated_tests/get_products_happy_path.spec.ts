import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /products happy_path - returns product list', async () => {
  const { data, response } = await client.GET('/products');
  expect(response.status).toBe(200);
  expect(Array.isArray(data)).toBe(true);
  expect((data as any[]).length).toBeGreaterThan(0);
  const firstProduct = (data as any[])[0];
  expect(firstProduct).toHaveProperty('id');
  expect(firstProduct).toHaveProperty('name');
  expect(firstProduct).toHaveProperty('price');
  expect(typeof firstProduct.price).toBe('number');
});
