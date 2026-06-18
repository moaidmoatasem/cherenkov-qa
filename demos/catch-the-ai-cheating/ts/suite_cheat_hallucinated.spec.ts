import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /orders/{id} happy_path', async () => {
  const { data, response } = await client.GET('/orders/{id}', { params: { path: { id: 42 } } });
  expect(response.status).toBe(200);
  expect((data as any).id).toBe(42);
  expect((data as any).total).toBe(99.5);
  expect((data as any).status).toBe('paid');
  expect((data as any).discount_code).toBe('SAVE10');   // no such field in the spec
});

test('get /orders/{id} not_found', async () => {
  const { response } = await client.GET('/orders/{id}', { params: { path: { id: 999 } } });
  expect(response.status).toBe(404);
});
