import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create customer happy path', async () => {
  const { data, response } = await client.POST('/v1/customers', {
    body: {
      email: 'test@example.com',
      name: 'Test Customer',
      phone: '+1234567890'
    }
  });
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
});