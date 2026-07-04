import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /pets happy_path golden_mut', async () => {
  const { data, response } = await client.GET('/pets');
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('status');
});
