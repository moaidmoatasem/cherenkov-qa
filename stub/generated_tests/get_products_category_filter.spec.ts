import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /products with category filter - only returns matching products', async () => {
  const { data, response } = await client.GET('/products', {
    params: { query: { category: 'tools' } }
  });
  expect(response.status).toBe(200);
  expect(Array.isArray(data)).toBe(true);
  // All returned products must belong to 'tools' category
  for (const product of (data as any[])) {
    expect(product.category).toBe('tools');
  }
});
