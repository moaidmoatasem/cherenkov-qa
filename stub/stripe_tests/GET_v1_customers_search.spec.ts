import { client } from '../client';
import { test, expect } from '@playwright/test';

test('search customers happy path', async () => {
  const { data, response } = await client.GET('/v1/customers/search', {
    params: {
      query: {
        query: 'name[eq]=John Doe'
      }
    }
  });
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('data');
});
