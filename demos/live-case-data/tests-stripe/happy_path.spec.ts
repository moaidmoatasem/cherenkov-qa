import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create charge happy path', async () => {
  const { data, response } = await client.POST('/v1/charges', {
    query: {
      amount: 100,
      currency: 'USD',
      source: 'tok_visa'
    }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
});