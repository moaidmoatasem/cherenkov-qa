import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create pet missing_name - returns 422', async () => {
  const { error, response } = await client.POST('/pet', {
    body: { id: 10, status: 'available' } as any
  });
  expect(response.status).toBe(422);
  expect(error).toBeTruthy();
  expect((error as any).detail).toBeTruthy();
});