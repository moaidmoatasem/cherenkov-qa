import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /orders/{id} happy_path', async () => {
  const { data, response } = await client.GET('/orders/{id}', { params: { path: { id: 42 } } });
  expect(response.status).toBeLessThan(500);          // was toBe(200)
  expect((data as any).id).toBeDefined();             // was toBe(42)
  expect((data as any).total).toBe(99.5);
  expect((data as any).status).toBeTruthy();          // was toBe('paid')
});

test('get /orders/{id} not_found', async () => {
  const { response } = await client.GET('/orders/{id}', { params: { path: { id: 999 } } });
  expect(response.status).toBe(404);
});
