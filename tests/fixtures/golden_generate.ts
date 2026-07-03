import { client } from '../client';
import { test, expect } from '@playwright/test';

test('GET /pets happy_path (status 200)', async () => {
  const { data, response } = await client.GET('/pets', {});
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
});
