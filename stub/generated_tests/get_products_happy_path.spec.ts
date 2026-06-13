import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /products happy_path - returns product list', async () => {
  const { data, response } = await client.GET('/products');
  expect(response.status).toBe(200);
  expect(Array.isArray(data)).toBe(true);
  expect((data as any[]).length).toBeGreaterThan(0);
});
