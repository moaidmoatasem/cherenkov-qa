import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create charge unauthorized - returns 401', async () => {
  const { error, response } = await client.POST('/v1/charges', {
    query: { amount: 100, currency: 'USD', source: 'tok_visa' }
  });
  expect(response.status).toBe(401);
  expect(error).toBeTruthy();
});