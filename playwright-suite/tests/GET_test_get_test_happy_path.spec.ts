import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get /test happy_path', async () => {
  const { data, response } = await client.GET('/test', {});
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
});
