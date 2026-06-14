import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get customers happy path', async () => {
  const { data, response } = await client.GET('/v1/customers');
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('data');
});
