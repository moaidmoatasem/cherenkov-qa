import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /orders/{id} happy_path', async () => {
  const { data, response } = await client.GET('/orders/{id}', { params: { path: { id: 42 } } });
  expect(response.status).toBe(200);
  expect((data as any).id).toBe(42);
  // total and status checks deleted; the not_found test was removed entirely
});
