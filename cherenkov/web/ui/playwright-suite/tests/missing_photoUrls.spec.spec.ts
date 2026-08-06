import { client } from '../client';
import { test, expect } from '@playwright/test';

test('add pet missing photoUrls - returns 422', async () => {
  const { error, response } = await client.POST('/pet', {
    body: { id: 10, name: 'doggie', status: 'available' }
  });
  expect(response.status).toBe(422);
  expect(error).toBeTruthy();
  expect((error as any).detail).toBeTruthy();
});